"""
models.py
Define la estructura de datos de una Actividad.
Fase 1 (MVP Local): sin cifrado todavía; eso se añade en Fase 2.
"""

import re
from dataclasses import dataclass, asdict, field
from datetime import datetime, date
from typing import Optional

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ActivityValidationError(ValueError):
    """Error de validación de datos de una actividad."""
    pass


@dataclass
class User:
    """
    Representa una cuenta de usuario.

    email: identificador de acceso (único, se normaliza a minúsculas)
    password_hash: hash de la contraseña (nunca se guarda en texto plano)
    id / created_at: metadatos asignados por la base de datos
    """
    email: str
    password_hash: str = ""
    id: Optional[int] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        self.validate()

    def validate(self):
        email = (self.email or "").strip()
        if not email or not EMAIL_RE.match(email):
            raise ActivityValidationError("Correo electrónico inválido.")
        self.email = email.lower()

    @classmethod
    def from_row(cls, row: tuple) -> "User":
        id_, email, password_hash, created_at = row
        obj = cls(email=email, password_hash=password_hash)
        obj.id = id_
        obj.created_at = created_at
        return obj


@dataclass
class Activity:
    """
    Representa una actividad/registro capturado por el usuario.

    id: identificador único (lo asigna la base de datos, None si es nuevo)
    title: título breve de la actividad (obligatorio)
    description: detalle opcional
    category: categoría libre (ej. 'trabajo', 'salud', 'estudio')
    activity_date: fecha de la actividad (YYYY-MM-DD)
    duration_minutes: duración en minutos (opcional, >= 0)
    created_at / updated_at: metadatos de auditoría (ISO 8601)
    """
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    activity_date: str = field(default_factory=lambda: date.today().isoformat())
    duration_minutes: Optional[int] = None
    attachment_path: Optional[str] = None
    is_public: bool = False
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    user_id: Optional[int] = None

    def __post_init__(self):
        self.validate()

    def validate(self):
        if not self.title or not self.title.strip():
            raise ActivityValidationError("El título es obligatorio.")
        if len(self.title) > 150:
            raise ActivityValidationError("El título no puede superar 150 caracteres.")

        try:
            datetime.strptime(self.activity_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            raise ActivityValidationError(
                "activity_date debe tener formato YYYY-MM-DD."
            )

        if self.duration_minutes is not None:
            if not isinstance(self.duration_minutes, int) or self.duration_minutes < 0:
                raise ActivityValidationError(
                    "duration_minutes debe ser un entero >= 0."
                )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row: tuple) -> "Activity":
        """Construye una Activity a partir de una fila de SQLite (SELECT * ...)."""
        (id_, title, description, category, activity_date,
         duration_minutes, attachment_path, created_at, updated_at, user_id,
         is_public) = row
        obj = cls(
            title=title,
            description=description,
            category=category,
            activity_date=activity_date,
            duration_minutes=duration_minutes,
            attachment_path=attachment_path,
            user_id=user_id,
            is_public=bool(is_public),
        )
        obj.id = id_
        obj.created_at = created_at
        obj.updated_at = updated_at
        return obj