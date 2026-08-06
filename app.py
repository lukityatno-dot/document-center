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


def get_db():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    return conn


@app.route("/")
def index():

    files = []

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    for nama_file in sorted(os.listdir(UPLOAD_FOLDER)):

        path = os.path.join(UPLOAD_FOLDER, nama_file)

        if os.path.isfile(path):

            ukuran = round(os.path.getsize(path) / 1024, 2)

            waktu = os.path.getmtime(path)

            tanggal = datetime.fromtimestamp(
                waktu
            ).strftime("%d-%m-%Y %H:%M")

            ext = os.path.splitext(nama_file)[1].lower()

            if ext == ".pdf":
                tipe = "PDF"
                icon = "bi-file-earmark-pdf text-danger"

            elif ext in [".doc", ".docx"]:
                tipe = "Word"
                icon = "bi-file-earmark-word text-primary"

            elif ext in [".xls", ".xlsx"]:
                tipe = "Excel"
                icon = "bi-file-earmark-excel text-success"

            elif ext in [".ppt", ".pptx"]:
                tipe = "PowerPoint"
                icon = "bi-file-earmark-ppt text-warning"

            elif ext in [".jpg", ".jpeg", ".png"]:
                tipe = "Gambar"
                icon = "bi-file-earmark-image text-info"

            elif ext in [".zip", ".rar", ".7z"]:
                tipe = "Arsip"
                icon = "bi-file-earmark-zip text-secondary"

            else:
                tipe = "File"
                icon = "bi-file-earmark"

            files.append({

                "nama": nama_file,

                "ukuran": ukuran,

                "tanggal": tanggal,

                "tipe": tipe,

                "icon": icon

            })

    return render_template(
        "index.html",
        files=files,
        user=session.get("user")
    )


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