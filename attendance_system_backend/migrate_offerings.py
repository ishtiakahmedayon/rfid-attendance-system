"""
One-time migration: adds CourseOfferings + Enrollments tables,
converts existing Sessions.course_code rows into a default offering
per course, and rewires Sessions to use offering_id.

Run once: python migrate_offerings.py
"""

from database import get_connection

DEFAULT_YEAR = 2025
DEFAULT_BATCH = "Legacy"

conn = get_connection()
cur = conn.cursor()

# 1. Create new tables (safe if they already exist)
cur.execute("""
CREATE TABLE IF NOT EXISTS CourseOfferings(
    offering_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL,
    academic_year INTEGER NOT NULL,
    batch TEXT NOT NULL,
    FOREIGN KEY(course_code) REFERENCES Courses(course_code),
    UNIQUE(course_code, academic_year, batch)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS Enrollments(
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    offering_id INTEGER NOT NULL,
    status TEXT DEFAULT 'Active',
    FOREIGN KEY(student_id) REFERENCES Students(student_id),
    FOREIGN KEY(offering_id) REFERENCES CourseOfferings(offering_id),
    UNIQUE(student_id, offering_id)
)
""")

# 2. Does Sessions still have the old course_code column?
cur.execute("PRAGMA table_info(Sessions)")
columns = [row["name"] for row in cur.fetchall()]

if "course_code" in columns:

    # Create one default offering per distinct existing course_code
    cur.execute("SELECT DISTINCT course_code FROM Sessions WHERE course_code IS NOT NULL")
    course_codes = [row["course_code"] for row in cur.fetchall()]

    code_to_offering = {}

    for code in course_codes:
        cur.execute("""
            INSERT OR IGNORE INTO CourseOfferings (course_code, academic_year, batch)
            VALUES (?,?,?)
        """, (code, DEFAULT_YEAR, DEFAULT_BATCH))

        cur.execute("""
            SELECT offering_id FROM CourseOfferings
            WHERE course_code=? AND academic_year=? AND batch=?
        """, (code, DEFAULT_YEAR, DEFAULT_BATCH))

        code_to_offering[code] = cur.fetchone()["offering_id"]

    # Rebuild Sessions with offering_id instead of course_code
    cur.execute("""
        CREATE TABLE Sessions_new(
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            offering_id INTEGER NOT NULL,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            status TEXT,
            FOREIGN KEY(offering_id) REFERENCES CourseOfferings(offering_id)
        )
    """)

    cur.execute("SELECT * FROM Sessions")
    old_sessions = cur.fetchall()

    for s in old_sessions:
        offering_id = code_to_offering.get(s["course_code"])
        cur.execute("""
            INSERT INTO Sessions_new
            (session_id, offering_id, date, start_time, end_time, status)
            VALUES (?,?,?,?,?,?)
        """, (s["session_id"], offering_id, s["date"], s["start_time"], s["end_time"], s["status"]))

    cur.execute("DROP TABLE Sessions")
    cur.execute("ALTER TABLE Sessions_new RENAME TO Sessions")

    print(f"Migrated {len(old_sessions)} sessions into {len(code_to_offering)} offering(s).")

else:
    print("Sessions already uses offering_id — nothing to migrate.")

# 3. Backfill Enrollments so existing students aren't locked out of legacy offerings
cur.execute("SELECT offering_id FROM CourseOfferings")
offering_ids = [row["offering_id"] for row in cur.fetchall()]

cur.execute("SELECT student_id FROM Students")
student_ids = [row["student_id"] for row in cur.fetchall()]

added = 0
for offering_id in offering_ids:
    for student_id in student_ids:
        cur.execute("""
            INSERT OR IGNORE INTO Enrollments (student_id, offering_id, status)
            VALUES (?,?,'Active')
        """, (student_id, offering_id))
        added += cur.rowcount if cur.rowcount > 0 else 0

conn.commit()
conn.close()

print(f"Backfilled enrollments (existing students -> legacy offerings): {added} rows added.")
print("Migration complete.")
