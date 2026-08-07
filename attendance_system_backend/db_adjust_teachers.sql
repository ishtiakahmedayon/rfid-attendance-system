-- Manual DB adjustment for teacher assignment support.
-- Run this against your SQLite database file.

CREATE TABLE IF NOT EXISTS Teachers(
    teacher_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    password TEXT NOT NULL
);

ALTER TABLE CourseOfferings
ADD COLUMN assigned_teacher_id TEXT REFERENCES Teachers(teacher_id);

-- Optional: example teacher row
-- INSERT INTO Teachers (teacher_id, name, password) VALUES ('t001', 'Teacher Name', 'teacher-pass');
