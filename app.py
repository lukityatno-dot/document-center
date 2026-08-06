from flask import (
    Flask,
    render_template,
    send_from_directory,
    request,
    redirect,
    url_for,
    session,
    flash
)
from flask_wtf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
import sqlite3
import os
from datetime import datetime
import hashlib
from functools import wraps

app = Flask(__name__)
app.static_folder = "static"

app.secret_key = os.getenv("SECRET_KEY", "document-center-elhotel")
app.config["UPLOAD_FOLDER"] = "files"
app.config["WTF_CSRF_TIME_LIMIT"] = None
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

CSRFProtect(app)

UPLOAD_FOLDER = app.config["UPLOAD_FOLDER"]
DATABASE = "database/document_center.db"
THUMB_FOLDER = os.path.join(app.static_folder, "thumbs")
os.makedirs(THUMB_FOLDER, exist_ok=True)

# Use absolute paths based on the app location so the service finds files regardless of CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'database', 'document_center.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, app.config.get('UPLOAD_FOLDER', 'files'))
THUMB_FOLDER = os.path.join(app.root_path, 'static', 'thumbs')

os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info('App BASE_DIR=%s', BASE_DIR)
logger.info('Database at %s', DATABASE)
logger.info('Upload folder at %s', UPLOAD_FOLDER)
logger.info('Thumb folder at %s', THUMB_FOLDER)

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".jpg", ".jpeg", ".png",
    ".zip", ".rar", ".7z",
}
POPUP_EXTENSIONS = {".jpg", ".jpeg", ".png"}
POPUP_FILES = ["popup.jpg", "popup.png"]

ICON_MAP = {
    ".pdf": ("PDF", "bi-file-earmark-pdf text-danger"),
    ".doc": ("Word", "bi-file-earmark-word text-primary"),
    ".docx": ("Word", "bi-file-earmark-word text-primary"),
    ".xls": ("Excel", "bi-file-earmark-excel text-success"),
    ".xlsx": ("Excel", "bi-file-earmark-excel text-success"),
    ".ppt": ("PowerPoint", "bi-file-earmark-ppt text-warning"),
    ".pptx": ("PowerPoint", "bi-file-earmark-ppt text-warning"),
    ".jpg": ("Gambar", "bi-file-earmark-image text-info"),
    ".jpeg": ("Gambar", "bi-file-earmark-image text-info"),
    ".png": ("Gambar", "bi-file-earmark-image text-info"),
    ".zip": ("Arsip", "bi-file-earmark-zip text-secondary"),
    ".rar": ("Arsip", "bi-file-earmark-zip text-secondary"),
    ".7z": ("Arsip", "bi-file-earmark-zip text-secondary"),
}


def allowed_file(filename):

    return "." in filename and os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def get_file_list():

    files = []
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    # load thumbnail mapping from DB when available for faster lookup
    thumb_map = {}
    try:
        with get_db() as conn:
            rows = conn.execute("SELECT filename, thumbnail FROM documents").fetchall()
            for r in rows:
                if r["thumbnail"]:
                    thumb_map[r["filename"]] = r["thumbnail"]
    except Exception:
        # ignore DB errors and fallback to filesystem check
        thumb_map = {}

    for nama_file in sorted(os.listdir(app.config["UPLOAD_FOLDER"])):
        path = os.path.join(app.config["UPLOAD_FOLDER"], nama_file)
        if not os.path.isfile(path):
            continue

        ukuran = round(os.path.getsize(path) / 1024, 2)
        tanggal = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%d-%m-%Y %H:%M")
        ext = os.path.splitext(nama_file)[1].lower()
        tipe, icon = ICON_MAP.get(ext, ("File", "bi-file-earmark"))

        # prefer DB-stored thumbnail path, fallback to filesystem
        thumb_rel = thumb_map.get(nama_file)
        if not thumb_rel:
            thumb_name = f"thumb_{nama_file}.jpg"
            thumb_path = os.path.join(app.static_folder, "thumbs", thumb_name)
            if os.path.exists(thumb_path):
                thumb_rel = f"thumbs/{thumb_name}"

        files.append({
            "nama": nama_file,
            "ukuran": ukuran,
            "tanggal": tanggal,
            "tipe": tipe,
            "icon": icon,
            "thumb": thumb_rel,
        })

    return files


def get_db():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    return conn


from flask_wtf.csrf import generate_csrf


def get_popup_image():

    for filename in POPUP_FILES:
        path = os.path.join(app.static_folder, "img", filename)
        if os.path.exists(path):
            return f"img/{filename}"

    return "img/popup.png"


def allowed_popup_file(filename):

    return "." in filename and os.path.splitext(filename)[1].lower() in POPUP_EXTENSIONS


@app.context_processor
def inject_popup_image():

    return {
        "popup_image": get_popup_image(),
        "csrf_token": generate_csrf,
    }


def generate_thumbnail(src_path, dest_path, size=(300, 300)):

    try:
        with Image.open(src_path) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            img.thumbnail(size)
            img.save(dest_path, format="JPEG", quality=85)
            return True
    except Exception:
        return False


def insert_document(filename, filesize, filetype):

    with get_db() as conn:
        conn.execute(
            "INSERT INTO documents (filename, filesize, filetype, thumbnail) VALUES (?, ?, ?, ?)",
            (filename, filesize, filetype, None)
        )


def insert_document_with_thumbnail(filename, filesize, filetype, thumbnail, checksum=None):

    with get_db() as conn:
        conn.execute(
            "INSERT INTO documents (filename, filesize, filetype, thumbnail, checksum) VALUES (?, ?, ?, ?, ?)",
            (filename, filesize, filetype, thumbnail, checksum)
        )


def compute_checksum(file_path):

    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_documents_thumbnail_column():

    with get_db() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()]
        if 'thumbnail' not in cols:
            conn.execute("ALTER TABLE documents ADD COLUMN thumbnail TEXT")
        if 'checksum' not in cols:
            conn.execute("ALTER TABLE documents ADD COLUMN checksum TEXT")


def log_download(filename, username, ip_address):

    with get_db() as conn:
        conn.execute(
            "INSERT INTO download_logs (filename, username, ip_address) VALUES (?, ?, ?)",
            (filename, username, ip_address)
        )


def delete_document_record(filename):

    with get_db() as conn:
        conn.execute(
            "DELETE FROM documents WHERE filename=?",
            (filename,)
        )


def get_stats():

    with get_db() as conn:
        stats_row = conn.execute(
            "SELECT COUNT(*) AS total_documents FROM documents"
        ).fetchone()
        downloads_row = conn.execute(
            "SELECT COUNT(*) AS total_downloads FROM download_logs"
        ).fetchone()

    return {
        "total_documents": stats_row["total_documents"] if stats_row else 0,
        "total_downloads": downloads_row["total_downloads"] if downloads_row else 0,
        "total_files": len(get_file_list()),
    }


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("user")
        if not user or user.get("role") != "Administrator":
            return "Forbidden", 403
        return f(*args, **kwargs)
    return decorated_function


# ensure DB schema includes thumbnail column when app starts
try:
    ensure_documents_thumbnail_column()
except Exception:
    pass


@app.route("/")
def index():

    user = session.get("user")
    stats = get_stats()

    return render_template("index.html", files=get_file_list(), user=user, stats=stats)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    # only allow authenticated users to upload (User, Manager, Administrator)
    user = session.get("user")
    if not user or user.get("role") not in ("User", "Manager", "Administrator"):
        return "Forbidden", 403

    if request.method == "POST":
        files = request.files.getlist("documents")
        if not files or all(not f.filename for f in files):
            return render_template("upload.html", user=session.get("user"), error="Tidak ada file yang dipilih.")

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

        uploaded = 0
        errors = []

        for file in files:
            if not file or file.filename == "":
                continue

            if not allowed_file(file.filename):
                errors.append(f"{file.filename}: Jenis file tidak diperbolehkan.")
                continue

            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            if os.path.exists(file_path):
                errors.append(f"{filename}: File sudah ada.")
                continue

            file.save(file_path)

            checksum = compute_checksum(file_path)
            try:
                with get_db() as conn:
                    existing = conn.execute("SELECT filename FROM documents WHERE checksum=?", (checksum,)).fetchone()
            except Exception:
                existing = None

            if existing:
                os.remove(file_path)
                errors.append(f"{filename}: File duplikat sudah ada sebagai {existing['filename']}.")
                continue

            ext = os.path.splitext(filename)[1].lower()
            thumb_rel = None
            if ext in {'.jpg', '.jpeg', '.png', '.gif'}:
                thumb_name = f"thumb_{filename}.jpg"
                thumb_path = os.path.join(app.static_folder, 'thumbs', thumb_name)
                ok = generate_thumbnail(file_path, thumb_path)
                if ok:
                    thumb_rel = f"thumbs/{thumb_name}"

            insert_document_with_thumbnail(
                filename,
                os.path.getsize(file_path),
                os.path.splitext(filename)[1].lower(),
                thumb_rel,
                checksum
            )
            uploaded += 1

        if uploaded:
            flash(f"{uploaded} dokumen berhasil diunggah.", "success")
        if errors:
            flash("; ".join(errors), "danger")

        return redirect(url_for("index"))

    return render_template("upload.html", user=session.get("user"))


@app.route("/replace_popup", methods=["GET", "POST"])
def replace_popup():

    user = session.get("user")
    if not user or user.get("role") not in ("Administrator", "Manager"):
        return "Forbidden", 403

    error = None

    if request.method == "POST":
        if "popup_file" not in request.files:
            error = "Tidak ada file yang dipilih."
        else:
            file = request.files["popup_file"]
            if not file or file.filename == "":
                error = "Tidak ada file yang dipilih."
            elif not allowed_popup_file(file.filename):
                error = "Jenis file tidak diperbolehkan. Gunakan JPG atau PNG."
            else:
                filename = secure_filename(file.filename)
                ext = os.path.splitext(filename)[1].lower()
                save_name = "popup.jpg" if ext in {".jpg", ".jpeg"} else "popup.png"
                save_path = os.path.join(app.static_folder, "img", save_name)
                file.save(save_path)
                other_name = "popup.png" if save_name == "popup.jpg" else "popup.jpg"
                other_path = os.path.join(app.static_folder, "img", other_name)
                if os.path.exists(other_path):
                    os.remove(other_path)

                flash("Gambar popup berhasil diganti.", "success")
                return redirect(url_for("index"))

    return render_template("replace_popup.html", user=user, error=error)


@app.route("/preview/<path:nama_file>")
def preview(nama_file):

    ext = os.path.splitext(nama_file)[1].lower()

    if ext == ".pdf":
        mimetype = "application/pdf"
    elif ext in {".jpg", ".jpeg", ".png", ".gif"}:
        mimetype = f"image/{ext.lstrip('.')}"
    else:
        return redirect(url_for("download", nama_file=nama_file))

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        nama_file,
        as_attachment=False,
        mimetype=mimetype
    )


@app.route("/download/<path:nama_file>")
def download(nama_file):

    user = session.get("user")
    username = user.get("username") if user else None
    ip_address = request.remote_addr
    log_download(nama_file, username, ip_address)

    return send_from_directory(

        app.config["UPLOAD_FOLDER"],

        nama_file,

        as_attachment=True

    )


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username=?",
                (username,)
            ).fetchone()

        if user:

            if check_password_hash(
                user["password"],
                password
            ):

                session["user"] = dict(user)
                flash("Login berhasil.", "success")
                return redirect(url_for("index"))

        return render_template(
            "login.html",
            error="Username atau Password salah."
        )

    return render_template("login.html")


@app.route("/delete/<path:nama_file>", methods=["POST"])
def delete_file(nama_file):

    user = session.get("user")

    if not user or user.get("role") not in ("Administrator", "Manager"):
        return "Forbidden", 403

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], nama_file)

    if os.path.isfile(file_path):
        os.remove(file_path)
        # remove thumbnail file if exists
        thumb_name = f"thumb_{nama_file}.jpg"
        thumb_path = os.path.join(app.static_folder, 'thumbs', thumb_name)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        delete_document_record(nama_file)
        flash("Dokumen berhasil dihapus.", "success")

    return redirect(url_for("index"))


@app.route("/delete_bulk", methods=["POST"])
def delete_bulk():

    user = session.get("user")

    if not user or user.get("role") not in ("Administrator", "Manager"):
        return "Forbidden", 403

    files_to_delete = request.form.getlist("documents")
    deleted_count = 0

    for nama_file in files_to_delete:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], nama_file)
        if os.path.isfile(file_path):
            os.remove(file_path)
            thumb_name = f"thumb_{nama_file}.jpg"
            thumb_path = os.path.join(app.static_folder, 'thumbs', thumb_name)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            delete_document_record(nama_file)
            deleted_count += 1

    if deleted_count:
        flash(f"{deleted_count} dokumen berhasil dihapus.", "success")
    else:
        flash("Tidak ada dokumen yang dihapus.", "warning")

    return redirect(url_for("index"))


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


@app.route('/admin')
@admin_required
def admin():
    with get_db() as conn:
        docs = conn.execute('SELECT * FROM documents ORDER BY created_at DESC').fetchall()

    return render_template('admin.html', documents=docs, user=session.get('user'))


@app.route('/admin/users')
@admin_required
def admin_users():
    with get_db() as conn:
        users = conn.execute('SELECT id, username, fullname, role, created_at FROM users ORDER BY created_at DESC').fetchall()

    return render_template('admin_users.html', users=users, user=session.get('user'))


@app.route('/admin/users/create', methods=['GET', 'POST'])
@admin_required
def admin_create_user():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        fullname = request.form.get('fullname')
        role = request.form.get('role') or 'User'

        if not username or not password or not fullname:
            error = 'Isi semua field yang diperlukan.'
        else:
            pw_hash = generate_password_hash(password)
            try:
                with get_db() as conn:
                    conn.execute('INSERT INTO users (username,password,fullname,role) VALUES (?,?,?,?)', (username, pw_hash, fullname, role))
                flash('User berhasil dibuat.', 'success')
                return redirect(url_for('admin_users'))
            except Exception as e:
                error = 'Gagal membuat user: ' + str(e)

    return render_template('user_form.html', action='create', error=error, user=session.get('user'))


@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    with get_db() as conn:
        u = conn.execute('SELECT id, username, fullname, role FROM users WHERE id=?', (user_id,)).fetchone()

    if not u:
        return 'Not found', 404

    error = None
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        role = request.form.get('role') or 'User'
        password = request.form.get('password')

        try:
            with get_db() as conn:
                if password:
                    pw_hash = generate_password_hash(password)
                    conn.execute('UPDATE users SET fullname=?, role=?, password=? WHERE id=?', (fullname, role, pw_hash, user_id))
                else:
                    conn.execute('UPDATE users SET fullname=?, role=? WHERE id=?', (fullname, role, user_id))
            flash('User berhasil diperbarui.', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            error = 'Gagal memperbarui user: ' + str(e)

    return render_template('user_form.html', action='edit', u=u, error=error, user=session.get('user'))


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    try:
        with get_db() as conn:
            conn.execute('DELETE FROM users WHERE id=?', (user_id,))
        flash('User dihapus.', 'success')
    except Exception as e:
        flash('Gagal menghapus user: ' + str(e), 'danger')

    return redirect(url_for('admin_users'))


if __name__ == "__main__":

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=True

    )