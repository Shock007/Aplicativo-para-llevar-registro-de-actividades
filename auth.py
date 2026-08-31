"""
auth.py
Capa de autenticación (primera capa de seguridad del proyecto).

- Las contraseñas nunca se guardan ni se comparan en texto plano: se usa
  werkzeug.security (PBKDF2 + salt aleatorio por usuario).
- La sesión de Flask (firmada con FLASK_SECRET_KEY) guarda solo el user_id,
  nunca la contraseña ni su hash.
- Esta es la base sobre la que en Fase 2 se construirá el cifrado de datos
  (la clave maestra de cifrado podrá derivarse de la contraseña del usuario).
"""

from functools import wraps

from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def validate_password_strength(password: str) -> None:
    from models import ActivityValidationError
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ActivityValidationError(
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )


def login_required(view):
    """Decorador: exige sesión iniciada antes de ejecutar la vista."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión para continuar.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user_id():
    return session.get("user_id")


def current_user_email():
    return session.get("user_email")

def current_enc_key():
    return session.get("enc_key")
