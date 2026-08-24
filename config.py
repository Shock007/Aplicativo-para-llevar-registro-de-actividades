"""
config.py
Configuración centralizada del proyecto.

Prepara ya el uso de variables de entorno (.env) para no tener que
refactorizar cuando en la Fase 2 se agregue la clave maestra de cifrado
y en la Fase 3 los tokens de GitHub/Google Drive/MEGA.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv es opcional en esta fase; si no está instalado,
    # simplemente se usan las variables de entorno del sistema (si existen).
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = Path(os.getenv("ACTIVITY_DB_PATH", DATA_DIR / "activities.db"))

# Reservado para Fase 2 (cifrado). Aún no se usa.
MASTER_KEY_ENV_VAR = "ACTIVITY_MASTER_KEY"