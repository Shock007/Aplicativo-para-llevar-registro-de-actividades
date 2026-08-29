"""
crypto.py
Capa de cifrado (Fase 2).
"""

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 600_000
KEY_LENGTH_BYTES = 32
SALT_LENGTH_BYTES = 16


class DecryptionError(Exception):
    pass


def derive_key(password: str, salt: bytes) -> bytes:
    if not isinstance(salt, (bytes, bytearray)):
        raise TypeError("salt debe ser bytes.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH_BYTES,
        salt=bytes(salt),
        iterations=PBKDF2_ITERATIONS,
    )
    raw_key = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


def encrypt_str(key: bytes, texto: str) -> str:
    f = Fernet(key)
    token = f.encrypt(texto.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_str(key: bytes, texto_cifrado: str) -> str:
    f = Fernet(key)
    try:
        data = f.decrypt(texto_cifrado.encode("utf-8"))
    except InvalidToken as exc:
        raise DecryptionError(
            "No se pudo descifrar el contenido: clave incorrecta o dato corrupto."
        ) from exc
    return data.decode("utf-8")