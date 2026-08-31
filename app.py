""" app.py Interfaz web (Fase 1 - MVP Local) """
import os
import uuid
import io
from datetime import date
from crypto import derive_key, encrypt_bytes, decrypt_bytes, DecryptionError
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, send_file
)
from werkzeug.utils import secure_filename
from config import BASE_DIR
from database import ActivityDatabase, UserDatabase
from models import Activity, ActivityValidationError, User
from auth import (
    current_enc_key, hash_password, verify_password, validate_password_strength,
    login_required, current_user_id, current_user_email,
)

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt", "docx", "xlsx", "csv"}
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

if not FLASK_SECRET_KEY:
    if FLASK_DEBUG:
        FLASK_SECRET_KEY = "dev-only-not-secure"
    else:
        raise RuntimeError(
            "FLASK_SECRET_KEY no está definida. Es obligatoria fuera de modo debug: "
            "sin ella, la sesión firmada (que ahora también transporta la clave de "
            "cifrado derivada en /login) quedaría protegida con un secreto público "
            "y predecible. Genera una con: "
            "python -c \"import secrets; print(secrets.token_hex(32))\" "
            "y agrégala a tu .env como FLASK_SECRET_KEY."
        )

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
db = ActivityDatabase()
users_db = UserDatabase()
CATEGORIES = ["trabajo", "estudio", "salud", "personal", "otro"]


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user_id():
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        try:
            validate_password_strength(password)
            if password != confirm_password:
                raise ActivityValidationError("Las contraseñas no coinciden.")
            user = User(email=email, password_hash=hash_password(password))
            saved = users_db.create(user)
            fernet_key = derive_key(password, bytes.fromhex(saved.encryption_salt))
            session["user_id"] = saved.id
            session["user_email"] = saved.email
            session["enc_key"] = fernet_key.decode("utf-8")
            flash("Cuenta creada correctamente.", "success")
            return redirect(url_for("index"))
        except ActivityValidationError as e:
            flash(str(e), "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user_id():
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = users_db.get_by_email(email)
        if user and verify_password(password, user.password_hash):
            if not user.encryption_salt:
                user.encryption_salt = users_db.ensure_encryption_salt(user.id)
            fernet_key = derive_key(password, bytes.fromhex(user.encryption_salt))
            session["user_id"] = user.id
            session["user_email"] = user.email
            session["enc_key"] = fernet_key.decode("utf-8")
            return redirect(url_for("index"))
        flash("Correo o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("login"))

def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def _save_attachment(file_storage, key) -> str | None:
    if not file_storage or not file_storage.filename:
        return None
    if not _allowed(file_storage.filename):
        raise ActivityValidationError(
            f"Tipo de archivo no permitido. Usa: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )
    safe_name = secure_filename(file_storage.filename)
    stored_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    raw = file_storage.read()
    encrypted = encrypt_bytes(key, raw)
    with open(UPLOAD_DIR / stored_name, "wb") as out:
        out.write(encrypted)
    return stored_name
    
def _today_stats(activities):
    today = date.today().isoformat()
    minutes = sum(a.duration_minutes or 0 for a in activities if a.activity_date == today)
    count = sum(1 for a in activities if a.activity_date == today)
    return {"minutes": minutes, "count": count}

@app.route("/", methods=["GET"])
@login_required
def index():
    uid = current_user_id()
    activities = db.list(user_id=uid, key=current_enc_key())
    return render_template(
        "index.html",
        activities=activities[:8],
        all_activities=activities,
        public_activities=db.list_public(),
        categories=CATEGORIES,
        today=date.today().isoformat(),
        stats=_today_stats(activities),
        user_email=current_user_email(),
    )

@app.route("/activities", methods=["POST"])
@login_required
def create_activity():
    try:
        attachment_path = _save_attachment(request.files.get("attachment"), current_enc_key())
        kwargs = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip() or None,
            "category": request.form.get("category") or None,
            "duration_minutes": (
                int(request.form["duration_minutes"]) if request.form.get("duration_minutes") else None
            ),
            "attachment_path": attachment_path,
            "is_public": request.form.get("visibility") == "publico",
        }
        activity_date = request.form.get("activity_date")
        if activity_date:
            kwargs["activity_date"] = activity_date
        activity = Activity(**kwargs)
        saved = db.add(activity, user_id=current_user_id(), key=current_enc_key())
        flash(f"Actividad “{saved.title}” registrada correctamente.", "success")
    except ActivityValidationError as e:
        flash(str(e), "error")
    except ValueError:
        flash("La duración debe ser un número entero de minutos.", "error")
    return redirect(url_for("index"))

@app.route("/activities/<int:activity_id>/edit", methods=["POST"])
@login_required
def edit_activity(activity_id):
    try:
        new_attachment = request.files.get("attachment")
        attachment_path = _save_attachment(new_attachment, current_enc_key()) if new_attachment and new_attachment.filename else None
        fields = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip() or None,
            "category": request.form.get("category") or None,
            "duration_minutes": int(request.form["duration_minutes"]) if request.form.get("duration_minutes") else None,
            "activity_date": request.form.get("activity_date"),
            "is_public": request.form.get("visibility") == "publico",
        }
        if attachment_path:
            fields["attachment_path"] = attachment_path

        updated = db.update(activity_id, user_id=current_user_id(), key=current_enc_key(), **fields)
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
@login_required
def delete_activity(activity_id):
    deleted = db.delete(activity_id, user_id=current_user_id())
    if deleted:
        flash(f"Actividad #{activity_id} eliminada correctamente.", "success")
    else:
        flash(f"No se pudo eliminar la actividad #{activity_id}.", "error")
    return redirect(url_for("index"))

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    safe_name = secure_filename(filename)
    filepath = UPLOAD_DIR / safe_name
    if not filepath.is_file():
        flash("Archivo no encontrado.", "error")
        return redirect(url_for("index"))

    with open(filepath, "rb") as f:
        raw = f.read()

    key = current_enc_key()
    try:
        data = decrypt_bytes(key, raw) if key else raw
    except DecryptionError:
        data = raw  # archivo legado (pre-Fase 2) o cifrado con otra clave

    display_name = safe_name.split("_", 1)[1] if "_" in safe_name else safe_name
    return send_file(io.BytesIO(data), download_name=display_name, as_attachment=False)

if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG, host="0.0.0.0", port=5000)