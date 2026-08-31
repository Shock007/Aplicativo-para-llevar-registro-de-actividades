"""
migrate_encrypt.py
Script de UN SOLO USO — Fase 2.

Recorre todas las cuentas de usuario y re-cifra las actividades PRIVADAS
(is_public = 0) que quedaron en texto plano desde la Fase 1, ahora que
database.py cifra title/description automáticamente en add()/update().

Las actividades PÚBLICAS (is_public = 1) se dejan intencionalmente en
texto plano: /list_public las expone sin clave de sesión (ver database.py).

Es seguro ejecutarlo varias veces: por cada campo intenta descifrarlo
primero con la clave del usuario; si tiene éxito, ya estaba cifrado y se
omite. Solo re-escribe los campos que siguen en texto plano.

Uso:
    python migrate_encrypt.py            # pide contraseña por cada cuenta
    python migrate_encrypt.py --dry-run  # solo reporta, no escribe nada

Se pide la contraseña de cada cuenta (no se puede derivar la clave sin
ella). Deja la entrada vacía para omitir una cuenta.
"""

import sqlite3
import sys
from getpass import getpass

from config import DB_PATH
from crypto import derive_key, encrypt_str, decrypt_str, DecryptionError
from database import UserDatabase
from auth import verify_password

DRY_RUN = "--dry-run" in sys.argv


def _connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _fetch_all_users(conn):
    return conn.execute(
        "SELECT id, email, password_hash, encryption_salt FROM users ORDER BY id"
    ).fetchall()


def _fetch_private_activities(conn, user_id):
    return conn.execute(
        "SELECT id, title, description FROM activities "
        "WHERE user_id = ? AND is_public = 0",
        (user_id,),
    ).fetchall()


def _already_encrypted(key: bytes, value: str) -> bool:
    """True si value descifra correctamente con key (ya está cifrado)."""
    try:
        decrypt_str(key, value)
        return True
    except DecryptionError:
        return False
    except Exception:
        # Token con formato inválido (no es Fernet) -> tratar como texto plano
        return False


def migrate_user(conn, users_db, user_row):
    user_id, email, password_hash, encryption_salt = user_row

    password = getpass(f"Contraseña para {email} (Enter para omitir): ")
    if not password:
        print(f"  omitida.")
        return 0, 0

    if not verify_password(password, password_hash):
        print(f"  contraseña incorrecta, se omite {email}.")
        return 0, 0

    if not encryption_salt:
        encryption_salt = users_db.ensure_encryption_salt(user_id)
        print(f"  (se generó encryption_salt retroactivo para {email})")

    key = derive_key(password, bytes.fromhex(encryption_salt))

    rows = _fetch_private_activities(conn, user_id)
    migrated = 0
    skipped = 0

    for activity_id, title, description in rows:
        new_title = title
        new_description = description
        changed = False

        if title is not None and not _already_encrypted(key, title):
            new_title = encrypt_str(key, title)
            changed = True

        if description is not None and not _already_encrypted(key, description):
            new_description = encrypt_str(key, description)
            changed = True

        if changed:
            migrated += 1
            if DRY_RUN:
                print(f"    [dry-run] actividad #{activity_id} sería cifrada.")
            else:
                conn.execute(
                    "UPDATE activities SET title = ?, description = ? WHERE id = ?",
                    (new_title, new_description, activity_id),
                )
        else:
            skipped += 1

    if not DRY_RUN:
        conn.commit()

    print(f"  {email}: {migrated} actividad(es) cifrada(s), {skipped} ya estaban al día.")
    return migrated, skipped


def main():
    print("=== Migración Fase 2: cifrado de actividades privadas ===")
    if DRY_RUN:
        print("(modo --dry-run: no se escribirá nada)\n")

    users_db = UserDatabase()
    conn = _connect()
    try:
        users = _fetch_all_users(conn)
        if not users:
            print("No hay usuarios registrados.")
            return

        total_migrated = 0
        total_skipped = 0
        for user_row in users:
            print(f"\nUsuario: {user_row[1]}")
            m, s = migrate_user(conn, users_db, user_row)
            total_migrated += m
            total_skipped += s

        print(f"\n=== Resumen: {total_migrated} actividad(es) cifradas, "
              f"{total_skipped} ya estaban cifradas u omitidas ===")
    finally:
        conn.close()


if __name__ == "__main__":
    main()