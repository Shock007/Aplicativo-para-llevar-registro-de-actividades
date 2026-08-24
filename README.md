# Activity Tracker (Registro de Actividades Cifrado)

## Estado actual: Fase 1 — MVP Local ✅

En esta fase el proyecto funciona 100% en local, sin cifrado ni nube todavía
(eso llega en Fase 2 y Fase 3). El objetivo es tener la lógica de negocio y
el modelo de datos sólidos antes de añadir seguridad y sincronización.

## Estructura

```
activity_tracker/
├── main.py          # CLI (punto de entrada)
├── models.py         # Modelo de datos Activity + validaciones
├── database.py        # Acceso a SQLite (CRUD)
├── config.py          # Rutas y variables de entorno
├── requirements.txt
├── .env.example
├── .gitignore
└── data/               # DB local (ignorada por git)
```

## Uso

```bash
pip install -r requirements.txt

python main.py add --title "Reunión de equipo" --category trabajo --date 2026-08-24 --duration 45
python main.py list
python main.py list --category trabajo
python main.py show 1
python main.py update 1 --duration 60
python main.py delete 1
```

## Próximas fases

- **Fase 2:** cifrado AES-256 (`cryptography`) con contraseña maestra antes
  de cualquier exportación o respaldo.
- **Fase 3:** sincronización con GitHub privado, Google Drive (`PyDrive2`) y/o
  MEGA (`mega.py`), siempre sobre datos ya cifrados.
- **Fase 4:** pruebas de restauración íntegra y verificación de que las
  llaves nunca se expongan.
