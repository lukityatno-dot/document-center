"""
Safe migration: create new documents table with `checksum` column (if missing), copy data, and swap tables.
Backs up original DB to document_center.db.bak before modifying.
"""
import sqlite3
import shutil
import os

DB = os.path.join(os.path.dirname(__file__), '..', 'database', 'document_center.db')
DB = os.path.normpath(DB)

BACKUP = DB + '.bak'

NEW_SCHEMA = '''
CREATE TABLE documents_new(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filesize REAL,
    filetype TEXT,
    thumbnail TEXT,
    checksum TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''

COPY_SQL = '''
INSERT INTO documents_new (filename, filesize, filetype, thumbnail, checksum, created_at)
SELECT filename, filesize, filetype, thumbnail, checksum, created_at FROM documents;
'''


def main():
    if not os.path.exists(DB):
        print('DB not found, aborting')
        return

    print(f'Backing up DB to {BACKUP}')
    shutil.copy2(DB, BACKUP)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(documents)").fetchall()]
    if 'checksum' in cols:
        print('checksum column already exists; nothing to do')
        conn.close()
        return

    print('Creating new documents table and copying data...')
    cur.executescript(NEW_SCHEMA)
    cur.executescript(COPY_SQL)

    # drop old table and rename
    cur.execute('DROP TABLE documents')
    cur.execute('ALTER TABLE documents_new RENAME TO documents')

    conn.commit()
    conn.close()

    print('Migration complete. Original DB backed up as .bak')


if __name__ == '__main__':
    main()
