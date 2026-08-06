"""
Report duplicate files based on checksum column.
"""
import os
import sqlite3

DB = os.path.join(os.path.dirname(__file__), '..', 'database', 'document_center.db')
DB = os.path.normpath(DB)


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute('SELECT checksum, GROUP_CONCAT(filename) FROM documents WHERE checksum IS NOT NULL GROUP BY checksum HAVING COUNT(*)>1')
    rows = cur.fetchall()
    if not rows:
        print('No duplicates found.')
    else:
        for checksum, names in rows:
            print(f'Duplicate checksum {checksum}: {names}')

    conn.close()

if __name__ == '__main__':
    main()
