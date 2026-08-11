import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = "database/document_center.db"

os.makedirs("database", exist_ok=True)

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

# ==========================
# USERS
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT UNIQUE NOT NULL,

    password TEXT NOT NULL,

    fullname TEXT NOT NULL,

    role TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

# ==========================
# DOCUMENTS
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS documents(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    filename TEXT NOT NULL,

    filesize REAL,

    filetype TEXT,
    
    thumbnail TEXT,

    checksum TEXT,

    category TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

# ==========================
# DOWNLOAD LOG
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS download_logs(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    filename TEXT,

    username TEXT,

    ip_address TEXT,

    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

# ==========================
# ADMIN DEFAULT
# ==========================

password = generate_password_hash("admin123")

cursor.execute("""

INSERT OR IGNORE INTO users

(username,password,fullname,role)

VALUES

(?,?,?,?)

""",

(

"admin",

password,

"Stefanus WH",

"Administrator"

)

)

conn.commit()

conn.close()

print("Database berhasil dibuat.")