from datetime import datetime
from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for

from database import get_connection

ui_bp = Blueprint("ui", __name__)


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user_role = session.get("role")
            if not user_role:
                return redirect(url_for("ui.login"))
            if role and user_role != role:
                return redirect(url_for("ui.teacher_dashboard" if user_role == "teacher" else "ui.student_dashboard"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


@ui_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT teacher_id, name
            FROM Teachers
            WHERE teacher_id = ? AND password = ?
            """,
            (username, password),
        )
        teacher = cur.fetchone()

        if teacher:
            conn.close()
            session.clear()
            session["role"] = "teacher"
            session["teacher_id"] = teacher["teacher_id"]
            session["teacher_name"] = teacher["name"]
            return redirect(url_for("ui.teacher_dashboard"))

        cur.execute(
            """
            SELECT student_id, name
            FROM Students
            WHERE student_id = ? AND name = ?
            """,
            (username, password),
        )
        student = cur.fetchone()

        conn.close()

        if student:
            session.clear()
            session["role"] = "student"
            session["student_id"] = student["student_id"]
            session["student_name"] = student["name"]
            return redirect(url_for("ui.student_dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html", error=None)


@ui_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("ui.login"))


@ui_bp.route("/teacher/dashboard")
@login_required(role="teacher")
def teacher_dashboard():
    teacher_id = session.get("teacher_id")
    selected_offering_id = request.args.get("offering_id", "").strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            CourseOfferings.offering_id,
            CourseOfferings.course_code,
            Courses.course_name,
            CourseOfferings.academic_year,
            CourseOfferings.batch
        FROM CourseOfferings
        JOIN Courses ON CourseOfferings.course_code = Courses.course_code
        WHERE CourseOfferings.assigned_teacher_id = ?
        ORDER BY CourseOfferings.academic_year DESC, CourseOfferings.offering_id DESC
        """,
        (teacher_id,),
    )
    offerings = cur.fetchall()

    offering_ids = [str(row["offering_id"]) for row in offerings]

    # Default to the first assigned course offering (tab-based view instead
    # of a manual offering/session picker).
    if selected_offering_id not in offering_ids and offering_ids:
        selected_offering_id = offering_ids[0]
    elif not offering_ids:
        selected_offering_id = ""

    sessions_data = []
    roster = []

    if selected_offering_id in offering_ids:
        cur.execute(
            """
            SELECT session_id, date, start_time, end_time, status
            FROM Sessions
            WHERE offering_id = ?
            ORDER BY date DESC, start_time DESC
            """,
            (selected_offering_id,),
        )
        sessions = cur.fetchall()

        for sess in sessions:
            cur.execute(
                """
                SELECT
                    Students.student_id,
                    Students.name,
                    Attendance.scan_time,
                    Attendance.status
                FROM Enrollments
                JOIN Students ON Students.student_id = Enrollments.student_id
                LEFT JOIN Attendance
                    ON Attendance.student_id = Enrollments.student_id
                    AND Attendance.session_id = ?
                WHERE Enrollments.offering_id = ?
                  AND Enrollments.status = 'Active'
                ORDER BY Students.name
                """,
                (sess["session_id"], selected_offering_id),
            )
            enrolled_rows = cur.fetchall()

            present_students = []
            absent_students = []
            for row in enrolled_rows:
                item = {
                    "student_id": row["student_id"],
                    "name": row["name"],
                    "scan_time": row["scan_time"],
                    "status": row["status"],
                }
                if row["status"] == "Present":
                    present_students.append(item)
                else:
                    absent_students.append(item)

            sessions_data.append(
                {
                    "session_id": sess["session_id"],
                    "date": sess["date"],
                    "start_time": sess["start_time"],
                    "end_time": sess["end_time"],
                    "status": sess["status"],
                    "present_count": len(present_students),
                    "absent_count": len(absent_students),
                    "present_students": present_students,
                    "absent_students": absent_students,
                }
            )

        # Class overview: every enrolled student's overall attendance for
        # this course, so the teacher can see the whole class at a glance
        # instead of only date-by-date.
        cur.execute(
            """
            SELECT
                Students.student_id,
                Students.name,
                Sessions.session_id,
                COALESCE(Attendance.status, 'Absent') AS status
            FROM Enrollments
            JOIN Students ON Students.student_id = Enrollments.student_id
            JOIN Sessions ON Sessions.offering_id = Enrollments.offering_id
            LEFT JOIN Attendance
                ON Attendance.student_id = Enrollments.student_id
                AND Attendance.session_id = Sessions.session_id
            WHERE Enrollments.offering_id = ?
              AND Enrollments.status = 'Active'
            ORDER BY Students.name
            """,
            (selected_offering_id,),
        )
        roster_rows = cur.fetchall()

        roster_by_student = {}
        for row in roster_rows:
            key = row["student_id"]
            entry = roster_by_student.setdefault(
                key,
                {
                    "student_id": row["student_id"],
                    "name": row["name"],
                    "present": 0,
                    "absent": 0,
                    "total": 0,
                },
            )
            entry["total"] += 1
            if row["status"] == "Present":
                entry["present"] += 1
            else:
                entry["absent"] += 1

        for entry in roster_by_student.values():
            pct = (entry["present"] / entry["total"] * 100) if entry["total"] else 0
            if pct < 60:
                level = "red"
            elif pct >= 80:
                level = "good"
            else:
                level = "warn"
            entry["percentage"] = round(pct, 1)
            entry["level"] = level
            roster.append(entry)

        roster.sort(key=lambda e: e["name"])

    # There's a single physical device today, so only one session can be
    # actively running at any moment -- figure out whether that's this
    # course's session, someone else's, or nothing at all, so the
    # dashboard can show the right Start/End controls.
    cur.execute(
        """
        SELECT
            Sessions.session_id,
            Sessions.offering_id,
            CourseOfferings.course_code
        FROM Sessions
        JOIN CourseOfferings ON CourseOfferings.offering_id = Sessions.offering_id
        WHERE Sessions.status = 'Open'
        ORDER BY Sessions.session_id DESC
        LIMIT 1
        """
    )
    global_open = cur.fetchone()

    conn.close()

    open_session_here = bool(
        global_open and str(global_open["offering_id"]) == str(selected_offering_id)
    )
    open_elsewhere_course_code = None
    if global_open and not open_session_here:
        open_elsewhere_course_code = global_open["course_code"]

    return render_template(
        "teacher_dashboard.html",
        teacher_name=session.get("teacher_name"),
        offerings=offerings,
        selected_offering_id=selected_offering_id,
        sessions_data=sessions_data,
        roster=roster,
        open_session_here=open_session_here,
        open_elsewhere_course_code=open_elsewhere_course_code,
    )


@ui_bp.route("/teacher/session/start", methods=["POST"])
@login_required(role="teacher")
def start_session_remote():
    teacher_id = session.get("teacher_id")
    offering_id = request.form.get("offering_id", "").strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT 1 FROM CourseOfferings
        WHERE offering_id = ? AND assigned_teacher_id = ?
        """,
        (offering_id, teacher_id),
    )
    owns_offering = cur.fetchone() is not None

    if owns_offering:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        # Only one device exists right now, so only one session can be
        # open at a time -- close out anything left open before starting
        # the new one (mirrors the same safeguard the device-side
        # /start_session endpoint already applies).
        cur.execute(
            "UPDATE Sessions SET status='Closed', end_time=? WHERE status='Open'",
            (time_str,),
        )
        cur.execute(
            """
            INSERT INTO Sessions (offering_id, date, start_time, status)
            VALUES (?, ?, ?, 'Open')
            """,
            (offering_id, date_str, time_str),
        )
        conn.commit()

    conn.close()

    return redirect(url_for("ui.teacher_dashboard", offering_id=offering_id))


@ui_bp.route("/teacher/session/stop", methods=["POST"])
@login_required(role="teacher")
def stop_session_remote():
    teacher_id = session.get("teacher_id")
    offering_id = request.form.get("offering_id", "").strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT 1 FROM CourseOfferings
        WHERE offering_id = ? AND assigned_teacher_id = ?
        """,
        (offering_id, teacher_id),
    )
    owns_offering = cur.fetchone() is not None

    if owns_offering:
        time_str = datetime.now().strftime("%H:%M:%S")
        cur.execute(
            """
            UPDATE Sessions
            SET status = 'Closed', end_time = ?
            WHERE offering_id = ? AND status = 'Open'
            """,
            (time_str, offering_id),
        )
        conn.commit()

    conn.close()

    return redirect(url_for("ui.teacher_dashboard", offering_id=offering_id))


@ui_bp.route("/student/dashboard")
@login_required(role="student")
def student_dashboard():
    student_id = session.get("student_id")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            Sessions.session_id,
            CourseOfferings.offering_id,
            Courses.course_code,
            Courses.course_name,
            Sessions.date,
            Sessions.start_time,
            Attendance.scan_time,
            COALESCE(Attendance.status, 'Absent') AS status
        FROM Enrollments
        JOIN CourseOfferings ON CourseOfferings.offering_id = Enrollments.offering_id
        JOIN Courses ON Courses.course_code = CourseOfferings.course_code
        JOIN Sessions ON Sessions.offering_id = CourseOfferings.offering_id
        LEFT JOIN Attendance
            ON Attendance.session_id = Sessions.session_id
            AND Attendance.student_id = Enrollments.student_id
        WHERE Enrollments.student_id = ?
          AND Enrollments.status = 'Active'
        ORDER BY Courses.course_name, Sessions.date DESC, Sessions.start_time DESC
        """,
        (student_id,),
    )
    rows = cur.fetchall()

    conn.close()

    # Group each attendance row under its enrolled course offering and
    # compute present/absent totals, attendance percentage, and the full
    # session-by-session history (date, time, present/absent status).
    courses_by_offering = {}
    for row in rows:
        key = row["offering_id"]
        course = courses_by_offering.setdefault(
            key,
            {
                "offering_id": row["offering_id"],
                "course_code": row["course_code"],
                "course_name": row["course_name"],
                "present": 0,
                "absent": 0,
                "total": 0,
                "sessions": [],
            },
        )
        course["total"] += 1
        if row["status"] == "Present":
            course["present"] += 1
        else:
            course["absent"] += 1
        course["sessions"].append(
            {
                "session_id": row["session_id"],
                "date": row["date"],
                "start_time": row["start_time"],
                "status": row["status"],
            }
        )

    courses = []
    for course in courses_by_offering.values():
        percentage = (course["present"] / course["total"] * 100) if course["total"] else 0
        if percentage < 60:
            level = "red"
        elif percentage >= 80:
            level = "good"
        else:
            level = "warn"
        course["percentage"] = round(percentage, 1)
        course["level"] = level
        courses.append(course)

    courses.sort(key=lambda c: c["course_name"])

    return render_template(
        "student_dashboard.html",
        student_name=session.get("student_name"),
        student_id=student_id,
        courses=courses,
    )