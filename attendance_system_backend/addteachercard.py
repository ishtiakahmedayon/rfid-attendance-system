"""
One-time migration: adds `rfid_uid` to Teachers, used by the device's
card-tap confirmation step when starting a session from the ESP32 menu.

SQLite's ALTER TABLE ... ADD COLUMN can't attach a UNIQUE constraint
directly, so uniqueness is enforced with a separate partial unique
index instead -- it only applies to non-NULL values, so multiple
teachers with no card assigned yet don't collide with each other.

Run once: python add_teacher_card.py
"""

from database import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("PRAGMA table_info(Teachers)")
existing_columns = {row["name"] for row in cur.fetchall()}

if "rfid_uid" in existing_columns:
    print("Teachers.rfid_uid already exists -- skipping column add.")
else:
    cur.execute("ALTER TABLE Teachers ADD COLUMN rfid_uid TEXT")
    print("Added Teachers.rfid_uid")

cur.execute(
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_teachers_rfid_uid
    ON Teachers(rfid_uid)
    WHERE rfid_uid IS NOT NULL
    """
)

conn.commit()
conn.close()

print("Teachers.rfid_uid is ready.")