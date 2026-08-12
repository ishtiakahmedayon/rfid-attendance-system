import sqlite3

from config import DATABASE

_SCHEMA_CHECKED = False


def _ensure_schema(conn):
    """Lightweight auto-migration so older attendance.db files pick up
    newly added columns without needing a manual SQL script."""
    global _SCHEMA_CHECKED
    if _SCHEMA_CHECKED:
        return

    cur = conn.cursor()

    cur.execute("PRAGMA table_info(Courses)")
    course_columns = [row["name"] for row in cur.fetchall()]
    if course_columns and "credits" not in course_columns:
        cur.execute("ALTER TABLE Courses ADD COLUMN credits INTEGER NOT NULL DEFAULT 0")

    cur.execute("PRAGMA table_info(CourseOfferings)")
    offering_columns = [row["name"] for row in cur.fetchall()]
    if offering_columns and "archived" not in offering_columns:
        cur.execute("ALTER TABLE CourseOfferings ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    _SCHEMA_CHECKED = True


def get_connection():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    _ensure_schema(conn)

    return conn
