"""
Shared logic for sending absence-notification emails for one session.

Used two ways:
  - Automatically, right after a session ends (dashboard Stop, or the
    device's own /end_session) -- no browser session/flash context
    needed here, since the device call has none.
  - Manually, via the "Notify Absentees" button, which still exists as
    a resend/fallback option and just calls the same function.

Never raises for "nothing to send" conditions (SMTP not configured, no
absentees, no email on file) -- those are reported back in the returned
summary dict instead, so a session ending never fails just because
email isn't set up yet.
"""

from database import get_connection
from email_utils import EmailNotConfigured, send_absence_email


def notify_absentees_for_session(session_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            Sessions.session_id,
            Sessions.offering_id,
            Sessions.date,
            Courses.course_code,
            Courses.course_name
        FROM Sessions
        JOIN CourseOfferings ON CourseOfferings.offering_id = Sessions.offering_id
        JOIN Courses ON Courses.course_code = CourseOfferings.course_code
        WHERE Sessions.session_id = ?
        """,
        (session_id,),
    )
    sess = cur.fetchone()

    if sess is None:
        conn.close()
        return {"sent": 0, "no_email": 0, "failed": 0, "absent_total": 0, "not_configured": False, "found": False}

    offering_id = sess["offering_id"]

    # Everyone actively enrolled who was NOT marked present in this
    # specific session counts as absent for this notification.
    cur.execute(
        """
        SELECT Students.student_id, Students.name, Students.email
        FROM Enrollments
        JOIN Students ON Students.student_id = Enrollments.student_id
        WHERE Enrollments.offering_id = ?
          AND Enrollments.status = 'Active'
          AND Students.student_id NOT IN (
              SELECT student_id FROM Attendance
              WHERE session_id = ? AND status = 'Present'
          )
        """,
        (offering_id, session_id),
    )
    absent_students = cur.fetchall()

    sent = 0
    no_email = 0
    failed = 0
    not_configured = False

    for student in absent_students:
        if not_configured:
            break

        if not student["email"]:
            no_email += 1
            continue

        # Overall attendance percentage for this course, not just this
        # one session -- matches what the student sees on their own
        # dashboard, so the number in the email isn't a surprise.
        cur.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN Attendance.status = 'Present' THEN 1 ELSE 0 END) AS present
            FROM Sessions
            LEFT JOIN Attendance
                ON Attendance.session_id = Sessions.session_id
                AND Attendance.student_id = ?
            WHERE Sessions.offering_id = ?
            """,
            (student["student_id"], offering_id),
        )
        counts = cur.fetchone()
        total = counts["total"] or 0
        present = counts["present"] or 0
        percentage = (present / total * 100) if total else 0

        try:
            send_absence_email(
                to_email=student["email"],
                student_name=student["name"],
                course_code=sess["course_code"],
                course_name=sess["course_name"],
                session_date=sess["date"],
                percentage=percentage,
            )
            sent += 1
        except EmailNotConfigured:
            not_configured = True
        except Exception:
            failed += 1

    conn.close()

    return {
        "sent": sent,
        "no_email": no_email,
        "failed": failed,
        "absent_total": len(absent_students),
        "not_configured": not_configured,
        "found": True,
    }


def summary_message(result):
    """Turns a notify_absentees_for_session() result into one
    human-readable line, or None if there's nothing worth reporting
    (e.g. email genuinely isn't set up yet -- that shouldn't nag the
    teacher on every single session end)."""

    if not result["found"] or result["not_configured"]:
        return None
    if result["absent_total"] == 0:
        return None

    parts = [f"Absence emails: sent to {result['sent']} of {result['absent_total']} absent student(s)."]
    if result["no_email"]:
        parts.append(f"{result['no_email']} had no email on file.")
    if result["failed"]:
        parts.append(f"{result['failed']} failed to send.")
    return " ".join(parts)