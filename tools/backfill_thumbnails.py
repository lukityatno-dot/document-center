"""
Backfill thumbnails column in the documents table using existing files in static/thumbs
Also fill checksum column if empty by computing SHA256 of files in `files/`.
"""
import os
import sqlite3
import hashlib

DB = os.path.join(os.path.dirname(__file__), '..', 'database', 'document_center.db')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'files')
THUMB_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'static', 'thumbs')

DB = os.path.normpath(DB)
UPLOAD_FOLDER = os.path.normpath(UPLOAD_FOLDER)
THUMB_FOLDER = os.path.normpath(THUMB_FOLDER)

def compute_checksum(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    updated = 0
    checked = 0

    for fname in os.listdir(UPLOAD_FOLDER):
        fpath = os.path.join(UPLOAD_FOLDER, fname)
        if not os.path.isfile(fpath):
            continue
        checked += 1
        thumb_name = f"thumb_{fname}.jpg"
        thumb_rel = None
        thumb_path = os.path.join(THUMB_FOLDER, thumb_name)
        if os.path.exists(thumb_path):
            thumb_rel = f"thumbs/{thumb_name}"

        checksum = compute_checksum(fpath)

        # update thumbnail and checksum
        cur.execute("SELECT id, thumbnail, checksum FROM documents WHERE filename=?", (fname,))
        row = cur.fetchone()
        if row:
            need_update = False
            updates = []
            if thumb_rel and (not row[1]):
                cur.execute("UPDATE documents SET thumbnail=? WHERE id=?", (thumb_rel, row[0]))
                need_update = True
            if checksum and (not row[2]):
                cur.execute("UPDATE documents SET checksum=? WHERE id=?", (checksum, row[0]))
                need_update = True
            if need_update:
                updated += 1
        else:
            # insert new record if missing
            cur.execute("INSERT INTO documents (filename, filesize, filetype, thumbnail, checksum) VALUES (?, ?, ?, ?, ?)",
                        (fname, os.path.getsize(fpath), os.path.splitext(fname)[1].lower(), thumb_rel, checksum))
            updated += 1

    conn.commit()
    conn.close()

    print(f"Checked {checked} files, updated/inserted {updated} rows.")


if __name__ == '__main__':
    main()
