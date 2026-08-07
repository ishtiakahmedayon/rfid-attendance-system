from database import get_connection

conn = get_connection()

cursor = conn.cursor()

# ---------------- Students ----------------

cursor.execute("""

CREATE TABLE IF NOT EXISTS Students(

student_id TEXT PRIMARY KEY,

name TEXT NOT NULL,

batch INTEGER,

rfid_uid TEXT UNIQUE

)

""")

# ---------------- Courses ----------------

cursor.execute("""

CREATE TABLE IF NOT EXISTS Courses(

course_code TEXT PRIMARY KEY,

course_name TEXT,

semester INTEGER

)

""")

# ---------------- Sessions ----------------

cursor.execute("""

CREATE TABLE IF NOT EXISTS Sessions(

session_id INTEGER PRIMARY KEY AUTOINCREMENT,

course_code TEXT,

date TEXT,

start_time TEXT,

end_time TEXT,

status TEXT

)

""")

# ---------------- Attendance ----------------

cursor.execute("""

CREATE TABLE IF NOT EXISTS Attendance(

attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,

session_id INTEGER,

student_id TEXT,

scan_time TEXT,

status TEXT

)

""")

conn.commit()

conn.close()

print("Database Created Successfully.")