from flask import (
    Flask,
    render_template,
    send_from_directory,
    request,
    redirect,
    url_for,
    session
)

from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

app.secret_key = "document-center-elhotel"

UPLOAD_FOLDER = "files"
DATABASE = "database/document_center.db"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".jpg", ".jpeg", ".png",
    ".zip", ".rar", ".7z",
}

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

    for nama_file in sorted(os.listdir(app.config["UPLOAD_FOLDER"])):
        path = os.path.join(app.config["UPLOAD_FOLDER"], nama_file)
        if not os.path.isfile(path):
            continue

        ukuran = round(os.path.getsize(path) / 1024, 2)
        tanggal = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%d-%m-%Y %H:%M")
        ext = os.path.splitext(nama_file)[1].lower()
        tipe, icon = ICON_MAP.get(ext, ("File", "bi-file-earmark"))

        files.append({
            "nama": nama_file,
            "ukuran": ukuran,
            "tanggal": tanggal,
            "tipe": tipe,
            "icon": icon,
        })

    return files


def get_db():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    return conn


@app.route("/")
def index():

    return render_template("index.html", files=get_file_list(), user=session.get("user"))


@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "POST":
        if "document" not in request.files:
            return render_template("upload.html", user=session.get("user"), error="Tidak ada file yang dipilih.")

        file = request.files["document"]

        if not file or file.filename == "":
            return render_template("upload.html", user=session.get("user"), error="Tidak ada file yang dipilih.")

        if not allowed_file(file.filename):
            return render_template("upload.html", user=session.get("user"), error="Jenis file tidak diperbolehkan.")

        filename = secure_filename(file.filename)
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        return redirect(url_for("index"))

    return render_template("upload.html", user=session.get("user"))


@app.route("/upload_document", methods=["GET", "POST"])
def upload_document():

    if request.method == "POST":
        if "document" not in request.files:
            return render_template("upload.html", user=session.get("user"), error="Tidak ada file yang dipilih.")

        file = request.files["document"]

        if not file or file.filename == "":
            return render_template("upload.html", user=session.get("user"), error="Tidak ada file yang dipilih.")

        if not allowed_file(file.filename):
            return render_template("upload.html", user=session.get("user"), error="Jenis file tidak diperbolehkan.")

        filename = secure_filename(file.filename)
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        return redirect(url_for("index"))

    return render_template("upload.html", user=session.get("user"))


@app.route("/preview/<path:nama_file>")
def preview(nama_file):

    ext = os.path.splitext(nama_file)[1].lower()

    if ext != ".pdf":
        return redirect(url_for("download", nama_file=nama_file))

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        nama_file,
        as_attachment=False,
        mimetype="application/pdf"
    )


@app.route("/download/<path:nama_file>")
def download(nama_file):

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

        conn = get_db()

        user = conn.execute(

            "SELECT * FROM users WHERE username=?",

            (username,)

        ).fetchone()

        conn.close()

        if user:

            if check_password_hash(
                user["password"],
                password
            ):

                session["user"] = dict(user)

                return redirect(url_for("index"))

        return render_template(

            "login.html",

            error="Username atau Password salah."

        )

    return render_template("login.html")


@app.route("/delete/<path:nama_file>", methods=["POST"])
def delete_file(nama_file):

    user = session.get("user")

    if not user or user.get("role") != "Administrator":
        return "Forbidden", 403

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], nama_file)

    if os.path.isfile(file_path):
        os.remove(file_path)

    return redirect(url_for("index"))

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


if __name__ == "__main__":

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=True

    )