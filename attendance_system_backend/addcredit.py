"""
One-time migration: adds a `credit` column to Courses (e.g. 3.0 credit
hours). Plain ADD COLUMN is safe here (unlike the batch removal) since
we're adding a nullable column, not dropping one -- no table rebuild
needed.

Run once: python add_credit_to_courses.py
"""

from database import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("PRAGMA table_info(Courses)")
existing_columns = {row["name"] for row in cur.fetchall()}

if "credit" in existing_columns:
    print("Courses.credit already exists -- nothing to do.")
else:
    cur.execute("ALTER TABLE Courses ADD COLUMN credit REAL")
    conn.commit()
    print("Added Courses.credit")

conn.close()