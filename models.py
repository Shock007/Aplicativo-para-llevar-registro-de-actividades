"""
models.py
Define la estructura de datos de una Actividad.
Fase 1 (MVP Local): sin cifrado todavía; eso se añade en Fase 2.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime, date
from typing import Optional


class ActivityValidationError(ValueError):
    """Error de validación de datos de una actividad."""
    pass


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
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

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
         duration_minutes, created_at, updated_at) = row
        obj = cls(
            title=title,
            description=description,
            category=category,
            activity_date=activity_date,
            duration_minutes=duration_minutes,
        )
        obj.id = id_
        obj.created_at = created_at
        obj.updated_at = updated_at
        return obj