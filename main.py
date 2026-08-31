"""
main.py
Interfaz de línea de comandos (CLI) para el MVP local.

database.py ahora requiere user_id en todas sus operaciones (modelo
multiusuario compartido con la interfaz web), así que el CLI necesita
autenticarse igual que la web antes de tocar la base de datos.

Autenticación (dos formas, en este orden de prioridad):
    1. Flags: --email correo@ejemplo.com --password ****
    2. Variables de entorno: ACTIVITY_CLI_EMAIL / ACTIVITY_CLI_PASSWORD

Ejemplos:
    python main.py --email tu@correo.com --password 1234abcd add --title "Reunión de equipo" --category trabajo --date 2026-08-24 --duration 45
    python main.py --email tu@correo.com --password 1234abcd list
    python main.py --email tu@correo.com --password 1234abcd list --category trabajo
    python main.py --email tu@correo.com --password 1234abcd show 1
    python main.py --email tu@correo.com --password 1234abcd update 1 --duration 60
    python main.py --email tu@correo.com --password 1234abcd delete 1
"""

import argparse
import os
import sys

from crypto import derive_key
from database import ActivityDatabase, UserDatabase
from models import Activity, ActivityValidationError
from auth import verify_password


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="activity-tracker",
        description="Registro local de actividades (Fase 1 - MVP).",
    )
    parser.add_argument(
        "--email", default=None,
        help="Correo de la cuenta (o var. de entorno ACTIVITY_CLI_EMAIL)",
    )
    parser.add_argument(
        "--password", default=None,
        help="Contraseña de la cuenta (o var. de entorno ACTIVITY_CLI_PASSWORD)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Registrar una nueva actividad")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--description", default=None)
    p_add.add_argument("--category", default=None)
    p_add.add_argument("--date", dest="activity_date", default=None,
                        help="YYYY-MM-DD (por defecto: hoy)")
    p_add.add_argument("--duration", dest="duration_minutes", type=int, default=None)

    p_list = sub.add_parser("list", help="Listar actividades")
    p_list.add_argument("--category", default=None)
    p_list.add_argument("--date", dest="activity_date", default=None)

    p_show = sub.add_parser("show", help="Ver el detalle de una actividad")
    p_show.add_argument("id", type=int)

    p_update = sub.add_parser("update", help="Actualizar una actividad")
    p_update.add_argument("id", type=int)
    p_update.add_argument("--title", default=None)
    p_update.add_argument("--description", default=None)
    p_update.add_argument("--category", default=None)
    p_update.add_argument("--date", dest="activity_date", default=None)
    p_update.add_argument("--duration", dest="duration_minutes", type=int, default=None)

    p_delete = sub.add_parser("delete", help="Eliminar una actividad")
    p_delete.add_argument("id", type=int)

    return parser


def authenticate(email: str | None, password: str | None):
    """Resuelve credenciales y devuelve (user_id, fernet_key)."""
    email = email or os.getenv("ACTIVITY_CLI_EMAIL")
    password = password or os.getenv("ACTIVITY_CLI_PASSWORD")

    if not email or not password:
        print(
            "Error: se requieren credenciales. Usa --email/--password o define "
            "ACTIVITY_CLI_EMAIL / ACTIVITY_CLI_PASSWORD.",
            file=sys.stderr,
        )
        sys.exit(1)

    users_db = UserDatabase()
    user = users_db.get_by_email(email)
    if not user or not verify_password(password, user.password_hash):
        print("Error: correo o contraseña incorrectos.", file=sys.stderr)
        sys.exit(1)

    if not user.encryption_salt:
        user.encryption_salt = users_db.ensure_encryption_salt(user.id)
    key = derive_key(password, bytes.fromhex(user.encryption_salt))

    return user.id, key


def print_activity(a: Activity):
    print(f"[{a.id}] {a.title}")
    print(f"    Fecha:      {a.activity_date}")
    print(f"    Categoría:  {a.category or '-'}")
    print(f"    Duración:   {a.duration_minutes if a.duration_minutes is not None else '-'} min")
    if a.description:
        print(f"    Detalle:    {a.description}")
    print(f"    Creado:     {a.created_at}   Actualizado: {a.updated_at}")


def main():
    parser = build_parser()
    args = parser.parse_args()

    user_id, key = authenticate(args.email, args.password)
    db = ActivityDatabase()

    try:
        if args.command == "add":
            kwargs = {
                "title": args.title,
                "description": args.description,
                "category": args.category,
                "duration_minutes": args.duration_minutes,
            }
            if args.activity_date:
                kwargs["activity_date"] = args.activity_date

            activity = Activity(**kwargs)
            saved = db.add(activity, user_id=user_id, key=key)
            print(f"Actividad registrada con id {saved.id}.")

        elif args.command == "list":
            activities = db.list(
                user_id=user_id,
                key=key,
                category=args.category,
                activity_date=args.activity_date,
            )
            if not activities:
                print("No hay actividades registradas.")
            for a in activities:
                print(f"[{a.id}] {a.activity_date} | {a.category or '-':<12} | {a.title}")

        elif args.command == "show":
            activity = db.get(args.id, user_id=user_id, key=key)
            if not activity:
                print(f"No existe una actividad con id {args.id}.", file=sys.stderr)
                sys.exit(1)
            print_activity(activity)

        elif args.command == "update":
            updated = db.update(
                args.id,
                user_id=user_id,
                key=key,
                title=args.title,
                description=args.description,
                category=args.category,
                activity_date=args.activity_date,
                duration_minutes=args.duration_minutes,
            )
            if not updated:
                print(f"No existe una actividad con id {args.id}.", file=sys.stderr)
                sys.exit(1)
            print("Actividad actualizada:")
            print_activity(updated)

        elif args.command == "delete":
            ok = db.delete(args.id, user_id=user_id)
            if not ok:
                print(f"No existe una actividad con id {args.id}.", file=sys.stderr)
                sys.exit(1)
            print(f"Actividad {args.id} eliminada.")

    except ActivityValidationError as e:
        print(f"Error de validación: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()