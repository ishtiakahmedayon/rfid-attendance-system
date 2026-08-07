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
    selected_session_id = request.args.get("session_id", "").strip()

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

    offering_ids = {str(row["offering_id"]) for row in offerings}
    sessions = []
    selected_offering = None

    if selected_offering_id and selected_offering_id in offering_ids:
        selected_offering = selected_offering_id
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

    present_students = []
    absent_students = []

    if selected_offering and selected_session_id:
        cur.execute(
            """
            SELECT 1
            FROM Sessions
            WHERE session_id = ? AND offering_id = ?
            """,
            (selected_session_id, selected_offering),
        )
        session_exists = cur.fetchone() is not None

        if session_exists:
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
                (selected_session_id, selected_offering),
            )
            enrolled_rows = cur.fetchall()

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

    conn.close()

    return render_template(
        "teacher_dashboard.html",
        teacher_name=session.get("teacher_name"),
        offerings=offerings,
        sessions=sessions,
        selected_offering_id=selected_offering_id,
        selected_session_id=selected_session_id,
        present_students=present_students,
        absent_students=absent_students,
    )


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
        ORDER BY Sessions.date DESC, Sessions.start_time DESC
        """,
        (student_id,),
    )
    rows = cur.fetchall()

    conn.close()

    return render_template(
        "student_dashboard.html",
        student_name=session.get("student_name"),
        student_id=student_id,
        rows=rows,
    )
