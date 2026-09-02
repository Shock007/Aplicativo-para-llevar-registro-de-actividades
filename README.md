# Activity Tracker (Registro de Actividades Cifrado)

## Estado actual: Fase 1 — MVP Local ✅

En esta fase el proyecto funciona 100% en local, sin cifrado ni nube todavía
(eso llega en Fase 2 y Fase 3). El objetivo es tener la lógica de negocio y
el modelo de datos sólidos antes de añadir seguridad y sincronización.

## Estructura

```
activity_tracker/
│
├── data/                       # Almacenamiento local (SQLite)
│   └── activities.db           # DB local original (Logs/Datos sensibles)
│
├── uploads/                    # Archivos adjuntos cifrados (.png, .pdf, etc.)
│
├── templates/                  # PLANTILLAS HTML
│   ├── login.html              # Autenticación original
│   ├── register.html           # Registro original
│   ├── index.html              # Dashboard original de Actividades/Logs
│   └── inventory/              # NUEVO: Vistas del módulo de inventario
│       ├── list.html           # Catálogo y estados de productos
│       └── edit.html           # Formulario con validación de clave/permisos
│
├── static/                     # RECURSOS ESTÁTICOS
│   ├── css/
│   │   ├── auth.css
│   │   ├── styles.css
│   │   └── inventory.css       # NUEVO: Estilos para el módulo de inventario
│   └── js/
│       ├── app.js
│       └── inventory.js        # NUEVO: Peticiones e interacción de inventario
│
├── inventory/                  # NUEVO MÓDULO (Aislado de la lógica de actividades)
│   ├── __init__.py
│   ├── db_connector.py         # Conector a la DB externa de la empresa (SQLAlchemy/Psycopg2)
│   ├── models.py               # Modelos de lectura (Catálogo) y edición (Cantidad/Estado)
│   └── services.py             # Lógica de validación de clave corporativa y permisos
│
├── auth.py                     # Autenticación local original (hash, sesiones, Fernet key)
├── config.py                   # Configuración global (se agregan credenciales de la DB externa)
├── crypto.py                   # Motor original de cifrado AES-256 / PBKDF2
├── database.py                 # Capa CRUD local original (ActivityDatabase / UserDatabase)
├── models.py                   # Dataclasses originales (Activity / User)
├── main.py                     # CLI original del rastreador de actividades
├── app.py                      # Servidor Flask (se registran las nuevas rutas del inventario)
├── migrate_encrypt.py          # Script de migración existente
├── requirements.txt            # Se agregan conectores de BD (ej. SQLAlchemy, psycopg2/PyMySQL)
└── test/
    └── test_integrity.py       # Pruebas existentes
```

## Uso — CLI

```bash
pip install -r requirements.txt

python main.py add --title "Reunión de equipo" --category trabajo --date 2026-08-24 --duration 45
python main.py list
python main.py list --category trabajo
python main.py show 1
python main.py update 1 --duration 60
python main.py delete 1
```

## Uso — Interfaz web

CLI y web comparten la misma base de datos (`database.py`/`models.py`); son
dos formas de ver y editar los mismos datos.

```bash
pip install -r requirements.txt
python app.py
# abrir http://localhost:5000
```

Pantalla única "Nueva actividad": título, categoría, fecha, duración,
descripción y un adjunto opcional (arrastrar y soltar). El panel lateral
muestra el total de minutos registrados hoy y las últimas actividades.
Los adjuntos se guardan en `uploads/` (ignorada por git).

## Próximas fases

- **Fase 2:** cifrado AES-256 (`cryptography`) con contraseña maestra antes
  de cualquier exportación o respaldo.
- **Fase 3:** sincronización con GitHub privado, Google Drive (`PyDrive2`) y/o
  MEGA (`mega.py`), siempre sobre datos ya cifrados.
- **Fase 4:** pruebas de restauración íntegra y verificación de que las
  llaves nunca se expongan.
