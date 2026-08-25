""" app.py Interfaz web (Fase 1 - MVP Local) """
import os
import uuid
from datetime import date
from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_from_directory
)
from werkzeug.utils import secure_filename
from config import BASE_DIR
from database import ActivityDatabase
from models import Activity, ActivityValidationError

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt", "docx", "xlsx", "csv"}

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-not-secure")
db = ActivityDatabase()
CATEGORIES = ["trabajo", "estudio", "salud", "personal", "otro"]

def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def _save_attachment(file_storage) -> str | None:
    if not file_storage or not file_storage.filename:
        return None
    if not _allowed(file_storage.filename):
        raise ActivityValidationError(
            f"Tipo de archivo no permitido. Usa: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )
    safe_name = secure_filename(file_storage.filename)
    stored_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_storage.save(UPLOAD_DIR / stored_name)
    return stored_name

def _today_stats(activities):
    today = date.today().isoformat()
    minutes = sum(a.duration_minutes or 0 for a in activities if a.activity_date == today)
    count = sum(1 for a in activities if a.activity_date == today)
    return {"minutes": minutes, "count": count}

@app.route("/", methods=["GET"])
def index():
    activities = db.list()
    return render_template(
        "index.html",
        activities=activities[:8],
        all_activities=activities,
        categories=CATEGORIES,
        today=date.today().isoformat(),
        stats=_today_stats(activities),
    )

@app.route("/activities", methods=["POST"])
def create_activity():
    try:
        attachment_path = _save_attachment(request.files.get("attachment"))
        kwargs = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip() or None,
            "category": request.form.get("category") or None,
            "duration_minutes": (
                int(request.form["duration_minutes"]) if request.form.get("duration_minutes") else None
            ),
            "attachment_path": attachment_path,
        }
        activity_date = request.form.get("activity_date")
        if activity_date:
            kwargs["activity_date"] = activity_date
        activity = Activity(**kwargs)
        saved = db.add(activity)
        flash(f"Actividad “{saved.title}” registrada correctamente.", "success")
    except ActivityValidationError as e:
        flash(str(e), "error")
    except ValueError:
        flash("La duración debe ser un número entero de minutos.", "error")
    return redirect(url_for("index"))

@app.route("/activities/<int:activity_id>/edit", methods=["POST"])
def edit_activity(activity_id):
    try:
        new_attachment = request.files.get("attachment")
        attachment_path = _save_attachment(new_attachment) if new_attachment and new_attachment.filename else None

        fields = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip() or None,
            "category": request.form.get("category") or None,
            "duration_minutes": int(request.form["duration_minutes"]) if request.form.get("duration_minutes") else None,
            "activity_date": request.form.get("activity_date"),
        }
        if attachment_path:
            fields["attachment_path"] = attachment_path

        updated = db.update(activity_id, **fields)
        if updated:
            flash(f"Actividad #{activity_id} actualizada correctamente.", "success")
        else:
            flash(f"No se encontró la actividad #{activity_id}.", "error")
    except ActivityValidationError as e:
        flash(str(e), "error")
    except ValueError:
        flash("Error en los datos ingresados.", "error")
    return redirect(url_for("index"))

@app.route("/activities/<int:activity_id>/delete", methods=["POST"])
def delete_activity(activity_id):
    deleted = db.delete(activity_id)
    if deleted:
        flash(f"Actividad #{activity_id} eliminada correctamente.", "success")
    else:
        flash(f"No se pudo eliminar la actividad #{activity_id}.", "error")
    return redirect(url_for("index"))

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)