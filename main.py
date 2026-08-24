"""
main.py
Interfaz de línea de comandos (CLI) para el MVP local.

Ejemplos:
    python main.py add --title "Reunión de equipo" --category trabajo --date 2026-08-24 --duration 45
    python main.py list
    python main.py list --category trabajo
    python main.py show 1
    python main.py update 1 --duration 60
    python main.py delete 1
"""

import argparse
import sys

from database import ActivityDatabase
from models import Activity, ActivityValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="activity-tracker",
        description="Registro local de actividades (Fase 1 - MVP).",
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
    db = ActivityDatabase()

    try:
        if args.command == "add":
            kwargs = {"title": args.title, "description": args.description,
                      "category": args.category, "duration_minutes": args.duration_minutes}
            if args.activity_date:
                kwargs["activity_date"] = args.activity_date
            activity = Activity(**kwargs)
            saved = db.add(activity)
            print(f"Actividad registrada con id {saved.id}.")

        elif args.command == "list":
            activities = db.list(category=args.category, activity_date=args.activity_date)
            if not activities:
                print("No hay actividades registradas.")
            for a in activities:
                print(f"[{a.id}] {a.activity_date} | {a.category or '-':<12} | {a.title}")

        elif args.command == "show":
            activity = db.get(args.id)
            if not activity:
                print(f"No existe una actividad con id {args.id}.", file=sys.stderr)
                sys.exit(1)
            print_activity(activity)

        elif args.command == "update":
            updated = db.update(
                args.id,
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
            ok = db.delete(args.id)
            if not ok:
                print(f"No existe una actividad con id {args.id}.", file=sys.stderr)
                sys.exit(1)
            print(f"Actividad {args.id} eliminada.")

    except ActivityValidationError as e:
        print(f"Error de validación: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()