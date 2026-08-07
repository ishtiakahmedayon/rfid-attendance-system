from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for

from config import TEACHER_PASSWORD, TEACHER_USERNAME
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

        if username == TEACHER_USERNAME and password == TEACHER_PASSWORD:
            session.clear()
            session["role"] = "teacher"
            session["username"] = username
            return redirect(url_for("ui.teacher_dashboard"))

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT student_id, name
            FROM Students
            WHERE student_id = ? AND rfid_uid = ?
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
    selected_course = request.args.get("course_code", "").strip()
    selected_date = request.args.get("date", "").strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT course_code, course_name FROM Courses ORDER BY course_code")
    courses = cur.fetchall()

    rows = []
    if selected_course and selected_date:
        cur.execute(
            """
            SELECT
                Sessions.session_id,
                Sessions.course_code,
                Sessions.date,
                Sessions.start_time,
                Students.student_id,
                Students.name,
                Attendance.scan_time,
                Attendance.status
            FROM Sessions
            JOIN Attendance ON Attendance.session_id = Sessions.session_id
            JOIN Students ON Students.student_id = Attendance.student_id
            WHERE Sessions.course_code = ?
              AND Sessions.date = ?
            ORDER BY Sessions.start_time, Students.name
            """,
            (selected_course, selected_date),
        )
        rows = cur.fetchall()

    conn.close()

    return render_template(
        "teacher_dashboard.html",
        courses=courses,
        selected_course=selected_course,
        selected_date=selected_date,
        rows=rows,
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
            Sessions.course_code,
            Courses.course_name,
            Sessions.date,
            Sessions.start_time,
            Attendance.scan_time,
            Attendance.status
        FROM Attendance
        JOIN Sessions ON Sessions.session_id = Attendance.session_id
        LEFT JOIN Courses ON Courses.course_code = Sessions.course_code
        WHERE Attendance.student_id = ?
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
