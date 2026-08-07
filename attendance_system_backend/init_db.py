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

password TEXT NOT NULL

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

# ---------------- Course Offerings ----------------

cursor.execute("""

CREATE TABLE IF NOT EXISTS CourseOfferings(

offering_id INTEGER PRIMARY KEY AUTOINCREMENT,

course_code TEXT NOT NULL,

academic_year INTEGER NOT NULL,

batch TEXT NOT NULL,

assigned_teacher_id TEXT,

FOREIGN KEY(course_code) REFERENCES Courses(course_code),

FOREIGN KEY(assigned_teacher_id) REFERENCES Teachers(teacher_id),

UNIQUE(course_code, academic_year, batch)

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

conn.commit()

conn.close()

print("Database Created Successfully.")
