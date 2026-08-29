"""
database.py
Capa de persistencia local en SQLite.
Fase 1 (MVP Local): datos en texto plano en disco local (uso personal/offline).
La sincronización a la nube (Fase 3) siempre pasará por el cifrado (Fase 2)
antes de tocar este módulo.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager

from config import DB_PATH
from models import Activity, ActivityValidationError, User

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    activity_date TEXT NOT NULL,
    duration_minutes INTEGER,
    attachment_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(activity_date);
CREATE INDEX IF NOT EXISTS idx_activities_category ON activities(category);
"""

USERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    encryption_salt TEXT,
    created_at TEXT NOT NULL
);
"""


class ActivityDatabase:
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(USERS_SCHEMA)
            conn.executescript(SCHEMA)
            # Migraciones: si la DB es de una versión anterior, se agregan columnas nuevas
            # ANTES de crear cualquier índice que dependa de ellas.
            user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "encryption_salt" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN encryption_salt TEXT")
            cols = [r[1] for r in conn.execute("PRAGMA table_info(activities)").fetchall()]
            if "attachment_path" not in cols:
                conn.execute("ALTER TABLE activities ADD COLUMN attachment_path TEXT")
            if "user_id" not in cols:
                conn.execute("ALTER TABLE activities ADD COLUMN user_id INTEGER")
            if "is_public" not in cols:
                conn.execute("ALTER TABLE activities ADD COLUMN is_public INTEGER NOT NULL DEFAULT 0")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_user ON activities(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_public ON activities(is_public)")

    def add(self, activity: Activity, user_id: int) -> Activity:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO activities
                   (title, description, category, activity_date, duration_minutes,
                    attachment_path, created_at, updated_at, user_id, is_public)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (activity.title, activity.description, activity.category,
                 activity.activity_date, activity.duration_minutes,
                 activity.attachment_path, now, now, user_id, int(activity.is_public)),
            )
            activity.id = cur.lastrowid
            activity.created_at = now
            activity.updated_at = now
            activity.user_id = user_id
        return activity

    def get(self, activity_id: int, user_id: int) -> Optional[Activity]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM activities WHERE id = ? AND user_id = ?",
                (activity_id, user_id),
            ).fetchone()
        return Activity.from_row(row) if row else None

    def list(self, user_id: int, category: Optional[str] = None,
              activity_date: Optional[str] = None) -> List[Activity]:
        query = "SELECT * FROM activities WHERE user_id = ?"
        params = [user_id]
        if category:
            query += " AND category = ?"
            params.append(category)
        if activity_date:
            query += " AND activity_date = ?"
            params.append(activity_date)
        query += " ORDER BY activity_date DESC, id DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [Activity.from_row(r) for r in rows]

    def update(self, activity_id: int, user_id: int, **fields) -> Optional[Activity]:
        current = self.get(activity_id, user_id)
        if not current:
            return None

        allowed = {"title", "description", "category", "activity_date",
                   "duration_minutes", "attachment_path", "is_public"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return current

        merged = current.to_dict()
        merged.update(updates)
        # Revalida los datos combinados antes de escribir
        Activity(
            title=merged["title"],
            description=merged["description"],
            category=merged["category"],
            activity_date=merged["activity_date"],
            duration_minutes=merged["duration_minutes"],
        )

        if "is_public" in updates:
            updates["is_public"] = int(updates["is_public"])

        now = datetime.now().isoformat(timespec="seconds")
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE activities SET {set_clause}, updated_at = ? WHERE id = ? AND user_id = ?",
                (*updates.values(), now, activity_id, user_id),
            )
        return self.get(activity_id, user_id)

    def list_public(self) -> List[dict]:
        """Actividades marcadas como públicas por cualquier usuario, con el
        correo del autor incluido (solo lectura, no expone user_id ni datos
        de sesión de otros usuarios)."""
        query = """
            SELECT activities.id, activities.title, activities.description,
                   activities.category, activities.activity_date,
                   activities.duration_minutes, activities.attachment_path,
                   users.email AS author_email
            FROM activities
            JOIN users ON users.id = activities.user_id
            WHERE activities.is_public = 1
            ORDER BY activities.activity_date DESC, activities.id DESC
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]

    def delete(self, activity_id: int, user_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM activities WHERE id = ? AND user_id = ?",
                (activity_id, user_id),
            )
        return cur.rowcount > 0
    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(USERS_SCHEMA)
            conn.executescript(SCHEMA)
            user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "encryption_salt" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN encryption_salt TEXT")
            cols = [r[1] for r in conn.execute("PRAGMA table_info(activities)").fetchall()]
        # ... resto de migraciones de activities sin cambios


class UserDatabase:
    """CRUD de cuentas de usuario. Las contraseñas siempre llegan ya hasheadas
    (ver auth.py) — esta capa nunca ve ni guarda texto plano."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(USERS_SCHEMA)

    def create(self, user: User) -> User:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                    (user.email, user.password_hash, now),
                )
            except sqlite3.IntegrityError:
                raise ActivityValidationError(
                    "Ya existe una cuenta registrada con ese correo electrónico."
                )
            user.id = cur.lastrowid
            user.created_at = now
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
            ).fetchone()
        return User.from_row(row) if row else None

    def get_by_id(self, user_id: int) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return User.from_row(row) if row else None

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(USERS_SCHEMA)
            user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "encryption_salt" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN encryption_salt TEXT")