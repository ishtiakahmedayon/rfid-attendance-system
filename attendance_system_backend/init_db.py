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

# ---------------- Teachers ----------------

cursor.execute("""

CREATE TABLE IF NOT EXISTS Teachers(

teacher_id TEXT PRIMARY KEY,

name TEXT NOT NULL,

password TEXT NOT NULL,

rfid_uid TEXT UNIQUE

)

""")

# ---------------- Courses ----------------

cursor.execute("""

CREATE TABLE IF NOT EXISTS Courses(

course_code TEXT PRIMARY KEY,

course_name TEXT,

semester INTEGER,

credit REAL

)

""")

# ---------------- Course Offerings ----------------

cursor.execute("""

CREATE TABLE IF NOT EXISTS CourseOfferings(

offering_id INTEGER PRIMARY KEY AUTOINCREMENT,

course_code TEXT NOT NULL,

academic_year INTEGER NOT NULL,

assigned_teacher_id TEXT,

FOREIGN KEY(course_code) REFERENCES Courses(course_code),

FOREIGN KEY(assigned_teacher_id) REFERENCES Teachers(teacher_id),

UNIQUE(course_code, academic_year)

)

""")

# ---------------- Enrollments ----------------

cursor.execute("""

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

# ---------------- Sessions ----------------

cursor.execute("""

CREATE TABLE IF NOT EXISTS Sessions(

session_id INTEGER PRIMARY KEY AUTOINCREMENT,

offering_id INTEGER NOT NULL,

date TEXT,

start_time TEXT,

end_time TEXT,

status TEXT,

FOREIGN KEY(offering_id) REFERENCES CourseOfferings(offering_id)

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

# ---------------- ArchivedOfferings ----------------
# NOTE: this table already existed in the live DB (added via a separate
# migration) but was missing from this fresh-install script -- added
# here so a brand-new deployment matches production.

cursor.execute("""

CREATE TABLE IF NOT EXISTS ArchivedOfferings(

offering_id INTEGER PRIMARY KEY REFERENCES CourseOfferings(offering_id),

archived_at TEXT NOT NULL,

archived_by TEXT REFERENCES Teachers(teacher_id)

)

""")

# ---------------- Admins ----------------
# No seeding here -- admin accounts are inserted manually. See
# create_admins_table.py / admin_password_tool.py for the workflow.

cursor.execute("""

CREATE TABLE IF NOT EXISTS Admins(

admin_id INTEGER PRIMARY KEY AUTOINCREMENT,

username TEXT NOT NULL UNIQUE,

password TEXT NOT NULL

)

""")

conn.commit()

conn.close()

print("Database Created Successfully.")