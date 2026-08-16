from datetime import datetime
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from database import get_connection
from email_utils import EmailNotConfigured, send_absence_email
from notify_utils import notify_absentees_for_session, notify_absentees_for_session_async, summary_message

ui_bp = Blueprint("ui", __name__)


ROLE_HOME_ROUTE = {
    "teacher": "ui.teacher_dashboard",
    "student": "ui.student_dashboard",
    "admin": "admin.dashboard",
}


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user_role = session.get("role")
            if not user_role:
                return redirect(url_for("ui.login"))
            if role and user_role != role:
                home = ROLE_HOME_ROUTE.get(user_role, "ui.login")
                return redirect(url_for(home))
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
            Courses.credit,
            CourseOfferings.academic_year
        FROM CourseOfferings
        JOIN Courses ON CourseOfferings.course_code = Courses.course_code
        WHERE CourseOfferings.assigned_teacher_id = ?
          AND CourseOfferings.offering_id NOT IN (SELECT offering_id FROM ArchivedOfferings)
        ORDER BY CourseOfferings.academic_year DESC, CourseOfferings.offering_id DESC
        """,
        (teacher_id,),
    )
    offerings = cur.fetchall()

    cur.execute(
        """
        SELECT
            CourseOfferings.offering_id,
            CourseOfferings.course_code,
            Courses.course_name,
            CourseOfferings.academic_year,
            ArchivedOfferings.archived_at
        FROM ArchivedOfferings
        JOIN CourseOfferings ON CourseOfferings.offering_id = ArchivedOfferings.offering_id
        JOIN Courses ON Courses.course_code = CourseOfferings.course_code
        WHERE CourseOfferings.assigned_teacher_id = ?
        ORDER BY ArchivedOfferings.archived_at DESC
        """,
        (teacher_id,),
    )
    archived_offerings = cur.fetchall()

    offering_ids = [str(row["offering_id"]) for row in offerings]

    # Default to the first assigned course offering (tab-based view instead
    # of a manual offering/session picker).
    if selected_offering_id not in offering_ids and offering_ids:
        selected_offering_id = offering_ids[0]
    elif not offering_ids:
        selected_offering_id = ""

    selected_offering = next(
        (o for o in offerings if str(o["offering_id"]) == selected_offering_id), None
    )

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
        # instead of only date-by-date. Sessions is LEFT JOINed so a
        # course with zero sessions held yet still lists its enrolled
        # students (with 0/0 counts) instead of showing nobody.
        cur.execute(
            """
            SELECT
                Students.student_id,
                Students.name,
                Sessions.session_id,
                COALESCE(Attendance.status, 'Absent') AS status
            FROM Enrollments
            JOIN Students ON Students.student_id = Enrollments.student_id
            LEFT JOIN Sessions ON Sessions.offering_id = Enrollments.offering_id
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

            if row["session_id"] is None:
                # No sessions held for this course yet -- student still
                # shows up on the roster, just with nothing to count.
                continue

            entry["total"] += 1
            if row["status"] == "Present":
                entry["present"] += 1
            else:
                entry["absent"] += 1

        for entry in roster_by_student.values():
            if entry["total"] == 0:
                entry["percentage"] = None
                entry["level"] = "none"
            else:
                pct = entry["present"] / entry["total"] * 100
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
        archived_offerings=archived_offerings,
        selected_offering_id=selected_offering_id,
        selected_offering=selected_offering,
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
    open_session = None

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
        cur.execute(
            "SELECT session_id FROM Sessions WHERE offering_id = ? AND status = 'Open'",
            (offering_id,),
        )
        open_session = cur.fetchone()

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

    if owns_offering and open_session:
        # Fire-and-forget: sending must never be able to hang or crash
        # the request that ends a session. See notify_utils.py for why
        # this matters in practice (some hosts, including Render, can
        # silently drop outbound SMTP connections).
        notify_absentees_for_session_async(open_session["session_id"])

    return redirect(url_for("ui.teacher_dashboard", offering_id=offering_id))


@ui_bp.route("/teacher/session/cancel", methods=["POST"])
@login_required(role="teacher")
def cancel_session_remote():
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
        cur.execute(
            "SELECT session_id FROM Sessions WHERE offering_id = ? AND status = 'Open'",
            (offering_id,),
        )
        open_session = cur.fetchone()

        if open_session:
            session_id = open_session["session_id"]
            # Cancel discards the session entirely -- unlike End, this
            # session should never count as a held class or show up in
            # anyone's attendance history, so both the scan records and
            # the session row itself are removed.
            cur.execute("DELETE FROM Attendance WHERE session_id = ?", (session_id,))
            cur.execute("DELETE FROM Sessions WHERE session_id = ?", (session_id,))
            conn.commit()

    conn.close()

    return redirect(url_for("ui.teacher_dashboard", offering_id=offering_id))


@ui_bp.route("/teacher/session/<int:session_id>/notify_absentees", methods=["POST"])
@login_required(role="teacher")
def notify_absentees(session_id):
    teacher_id = session.get("teacher_id")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1
        FROM Sessions
        JOIN CourseOfferings ON CourseOfferings.offering_id = Sessions.offering_id
        WHERE Sessions.session_id = ? AND CourseOfferings.assigned_teacher_id = ?
        """,
        (session_id, teacher_id),
    )
    owns_session = cur.fetchone() is not None
    cur.execute("SELECT offering_id FROM Sessions WHERE session_id = ?", (session_id,))
    row = cur.fetchone()
    conn.close()

    if not owns_session or row is None:
        flash("Could not send notifications -- session not found.")
        return redirect(url_for("ui.teacher_dashboard"))

    offering_id = row["offering_id"]

    result = notify_absentees_for_session(session_id)
    if result["not_configured"]:
        flash("Could not send notifications -- email is not configured on the server yet.")
    else:
        message = summary_message(result)
        flash(message or "No absent students to notify for this session.")

    return redirect(url_for("ui.teacher_dashboard", offering_id=offering_id))


@ui_bp.route("/teacher/course/archive", methods=["POST"])
@login_required(role="teacher")
def archive_course():
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
        cur.execute(
            "SELECT 1 FROM Sessions WHERE offering_id = ? AND status = 'Open'",
            (offering_id,),
        )
        has_live_session = cur.fetchone() is not None

        if not has_live_session:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                """
                INSERT OR IGNORE INTO ArchivedOfferings (offering_id, archived_at, archived_by)
                VALUES (?, ?, ?)
                """,
                (offering_id, now_str, teacher_id),
            )
            conn.commit()

    conn.close()

    # The archived course drops out of the tab bar, so don't try to
    # re-select it -- fall back to the dashboard's own default.
    return redirect(url_for("ui.teacher_dashboard"))


@ui_bp.route("/teacher/course/unarchive", methods=["POST"])
@login_required(role="teacher")
def unarchive_course():
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
        cur.execute("DELETE FROM ArchivedOfferings WHERE offering_id = ?", (offering_id,))
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
            Courses.credit,
            Sessions.date,
            Sessions.start_time,
            Attendance.scan_time,
            COALESCE(Attendance.status, 'Absent') AS status
        FROM Enrollments
        JOIN CourseOfferings ON CourseOfferings.offering_id = Enrollments.offering_id
        JOIN Courses ON Courses.course_code = CourseOfferings.course_code
        LEFT JOIN Sessions ON Sessions.offering_id = CourseOfferings.offering_id
        LEFT JOIN Attendance
            ON Attendance.session_id = Sessions.session_id
            AND Attendance.student_id = Enrollments.student_id
        WHERE Enrollments.student_id = ?
          AND Enrollments.status = 'Active'
          AND CourseOfferings.offering_id NOT IN (SELECT offering_id FROM ArchivedOfferings)
        ORDER BY Courses.course_name, Sessions.date DESC, Sessions.start_time DESC
        """,
        (student_id,),
    )
    rows = cur.fetchall()

    conn.close()

    # Group each attendance row under its enrolled course offering and
    # compute present/absent totals, attendance percentage, and the full
    # session-by-session history (date, time, present/absent status).
    # The Sessions table is LEFT JOINed above so a course with zero
    # sessions still produces one row (all Session/Attendance fields
    # NULL) instead of disappearing entirely -- that row just doesn't
    # contribute to the counts or session list below.
    # Archived offerings are excluded above, so an archived course drops
    # out of the student's view entirely as soon as the teacher archives it.
    courses_by_offering = {}
    for row in rows:
        key = row["offering_id"]
        course = courses_by_offering.setdefault(
            key,
            {
                "offering_id": row["offering_id"],
                "course_code": row["course_code"],
                "course_name": row["course_name"],
                "credit": row["credit"],
                "present": 0,
                "absent": 0,
                "total": 0,
                "sessions": [],
            },
        )

        if row["session_id"] is None:
            # No sessions held yet for this course -- keep the course
            # card, just with nothing to count.
            continue

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
        if course["total"] == 0:
            # No sessions yet -- neutral state, not a 0% (which would
            # misleadingly show up red).
            course["percentage"] = None
            course["level"] = "none"
        else:
            percentage = course["present"] / course["total"] * 100
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