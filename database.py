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
from models import Activity

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    activity_date TEXT NOT NULL,
    duration_minutes INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(activity_date);
CREATE INDEX IF NOT EXISTS idx_activities_category ON activities(category);
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
            conn.executescript(SCHEMA)

    def add(self, activity: Activity) -> Activity:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO activities
                   (title, description, category, activity_date, duration_minutes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (activity.title, activity.description, activity.category,
                 activity.activity_date, activity.duration_minutes, now, now),
            )
            activity.id = cur.lastrowid
            activity.created_at = now
            activity.updated_at = now
        return activity

    def get(self, activity_id: int) -> Optional[Activity]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM activities WHERE id = ?", (activity_id,)
            ).fetchone()
        return Activity.from_row(row) if row else None

    def list(self, category: Optional[str] = None,
              activity_date: Optional[str] = None) -> List[Activity]:
        query = "SELECT * FROM activities WHERE 1=1"
        params = []
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

    def update(self, activity_id: int, **fields) -> Optional[Activity]:
        current = self.get(activity_id)
        if not current:
            return None

        allowed = {"title", "description", "category", "activity_date", "duration_minutes"}
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

        now = datetime.now().isoformat(timespec="seconds")
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE activities SET {set_clause}, updated_at = ? WHERE id = ?",
                (*updates.values(), now, activity_id),
            )
        return self.get(activity_id)

    def delete(self, activity_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        return cur.rowcount > 0