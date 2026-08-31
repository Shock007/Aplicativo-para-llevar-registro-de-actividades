"""
tests/test_integrity.py
Fase 2 — pruebas de integridad del cifrado.

1. Round-trip: cifrar -> descifrar debe devolver siempre el texto original.
2. Verificación de que activities.db NO expone title/description en claro
   para actividades privadas, leyendo la fila cruda con sqlite3 (igual que
   lo haría cualquier lector de SQLite externo).
3. Casos límite: actividades públicas (sí quedan en claro, por diseño),
   compatibilidad con filas legadas (pre-Fase 2) sin cifrar, y clave
   incorrecta.

Ejecutar con:
    pip install pytest --break-system-packages
    pytest tests/ -v
"""

import sqlite3

import pytest

from crypto import derive_key, encrypt_str, decrypt_str, DecryptionError
from database import ActivityDatabase, UserDatabase
from models import Activity, User
from auth import hash_password


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_activities.db"


@pytest.fixture
def activity_db(db_path):
    return ActivityDatabase(db_path=db_path)


@pytest.fixture
def user_db(db_path):
    return UserDatabase(db_path=db_path)


@pytest.fixture
def user_with_key(user_db):
    """Crea un usuario y devuelve (user, fernet_key)."""
    password = "correcto-caballo-batería-grapa"
    user = user_db.create(User(email="test@example.com", password_hash=hash_password(password)))
    key = derive_key(password, bytes.fromhex(user.encryption_salt))
    return user, key


# ---------------------------------------------------------------------------
# 1. Round-trip: cifrar -> descifrar devuelve el original
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto", [
    "Reunión de planeación",
    "",  # cadena vacía
    "á é í ó ú ñ 中文 🎉 emoji mixto",
    "Línea 1\nLínea 2\tcon tab",
    "x" * 5000,  # texto largo
])
def test_roundtrip_encrypt_decrypt(texto):
    key = derive_key("mi-contraseña-segura", b"0123456789abcdef")
    cifrado = encrypt_str(key, texto)
    assert cifrado != texto
    descifrado = decrypt_str(key, cifrado)
    assert descifrado == texto


def test_decrypt_con_clave_incorrecta_falla():
    key_correcta = derive_key("clave-buena", b"0123456789abcdef")
    key_incorrecta = derive_key("clave-mala", b"0123456789abcdef")
    cifrado = encrypt_str(key_correcta, "dato sensible")
    with pytest.raises(DecryptionError):
        decrypt_str(key_incorrecta, cifrado)


def test_mismo_texto_produce_cifrados_distintos():
    """Fernet incluye IV/nonce aleatorio: dos cifrados del mismo texto
    no deben coincidir (evita firmas de texto repetido en la DB)."""
    key = derive_key("clave", b"0123456789abcdef")
    a = encrypt_str(key, "actividad repetida")
    b = encrypt_str(key, "actividad repetida")
    assert a != b
    assert decrypt_str(key, a) == decrypt_str(key, b) == "actividad repetida"


# ---------------------------------------------------------------------------
# 2. La DB en disco no expone title/description en claro (actividad privada)
# ---------------------------------------------------------------------------

def _raw_row(db_path, activity_id):
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT title, description, is_public FROM activities WHERE id = ?",
        (activity_id,),
    ).fetchone()
    conn.close()
    return row


def test_actividad_privada_no_expone_texto_plano_en_disco(activity_db, user_with_key, db_path):
    user, key = user_with_key
    plaintext_title = "Terapia psicológica semanal"
    plaintext_desc = "Notas confidenciales de la sesión"

    saved = activity_db.add(
        Activity(title=plaintext_title, description=plaintext_desc, is_public=False),
        user_id=user.id,
        key=key,
    )

    raw_title, raw_desc, raw_is_public = _raw_row(db_path, saved.id)

    # Lo que hay físicamente en el archivo .db no debe ser el texto original.
    assert raw_title != plaintext_title
    assert raw_desc != plaintext_desc
    assert plaintext_title not in raw_title
    assert plaintext_desc not in raw_desc
    assert raw_is_public == 0

    # Pero descifrando con la clave correcta se recupera el original.
    assert decrypt_str(key, raw_title) == plaintext_title
    assert decrypt_str(key, raw_desc) == plaintext_desc

    # Y la capa de alto nivel (lo que ve la app) también coincide.
    fetched = activity_db.get(saved.id, user_id=user.id, key=key)
    assert fetched.title == plaintext_title
    assert fetched.description == plaintext_desc


def test_actividad_publica_queda_en_claro_por_diseno(activity_db, user_with_key, db_path):
    """Las actividades públicas se muestran sin sesión en /list_public,
    por lo que intencionalmente NO se cifran. Se documenta ese
    comportamiento para que no se confunda con un bug."""
    user, key = user_with_key
    plaintext_title = "Maratón de lectura (evento público)"

    saved = activity_db.add(
        Activity(title=plaintext_title, is_public=True),
        user_id=user.id,
        key=key,
    )

    raw_title, _, raw_is_public = _raw_row(db_path, saved.id)
    assert raw_is_public == 1
    assert raw_title == plaintext_title


def test_update_re_cifra_con_la_clave_correcta(activity_db, user_with_key, db_path):
    user, key = user_with_key
    saved = activity_db.add(
        Activity(title="original", description="desc original", is_public=False),
        user_id=user.id, key=key,
    )
    activity_db.update(saved.id, user_id=user.id, key=key, title="editado")

    raw_title, raw_desc, _ = _raw_row(db_path, saved.id)
    assert raw_title != "editado"
    assert decrypt_str(key, raw_title) == "editado"
    # La descripción no se tocó en el update, pero sigue descifrando bien.
    assert decrypt_str(key, raw_desc) == "desc original"


# ---------------------------------------------------------------------------
# 3. Compatibilidad con filas legadas (pre-Fase 2, sin cifrar) y con
#    la clave ausente
# ---------------------------------------------------------------------------

def test_fila_legada_sin_cifrar_se_lee_igual_por_compatibilidad(activity_db, user_with_key, db_path):
    """Simula una actividad insertada antes de la Fase 2 (texto plano),
    sin pasar por migrate_encrypt.py. database.py debe seguir mostrándola
    (fallback silencioso) en vez de romper."""
    user, key = user_with_key
    now = "2026-01-01T00:00:00"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO activities (title, description, category, activity_date, "
        "duration_minutes, attachment_path, created_at, updated_at, user_id, is_public) "
        "VALUES (?, NULL, NULL, ?, NULL, NULL, ?, ?, ?, 0)",
        ("actividad legada sin cifrar", "2026-01-01", now, now, user.id),
    )
    conn.commit()
    activity_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    fetched = activity_db.get(activity_id, user_id=user.id, key=key)
    assert fetched.title == "actividad legada sin cifrar"


def test_sin_clave_no_descifra_pero_no_revienta(activity_db, user_with_key):
    user, key = user_with_key
    saved = activity_db.add(
        Activity(title="privado", is_public=False), user_id=user.id, key=key,
    )
    fetched = activity_db.get(saved.id, user_id=user.id, key=None)
    # Sin clave se devuelve el valor crudo (cifrado), no se lanza excepción.
    assert fetched.title != "privado"