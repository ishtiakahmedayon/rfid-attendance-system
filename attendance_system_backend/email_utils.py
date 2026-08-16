import smtplib
from email.mime.text import MIMEText

from config import SMTP_FROM_NAME, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER


class EmailNotConfigured(Exception):
    """Raised when SMTP_USER/SMTP_PASSWORD aren't set."""


def _build_absence_email(student_name, course_code, course_name, session_date, percentage):
    percentage_display = f"{percentage:.1f}%"

    if percentage < 60:
        tail = (
            "This is below the minimum attendance requirement. Please make sure to "
            "attend upcoming classes to avoid academic penalties."
        )
    else:
        tail = "You're still in good standing overall, but please try not to miss further classes."

    subject = f"Attendance Notice — {course_code} {course_name}"

    body = (
        f"Hi {student_name},\n\n"
        f"You missed a class of the course {course_name} ({course_code}) on {session_date}.\n\n"
        f"Your current attendance percentage for this course is {percentage_display}.\n\n"
        f"{tail}\n\n"
        f"Regards,\n"
        f"{course_name} Attendance System"
    )

    return subject, body


def send_absence_email(to_email, student_name, course_code, course_name, session_date, percentage):
    """Sends one absence-notification email. Raises EmailNotConfigured if
    SMTP credentials aren't set, or the underlying smtplib exception on
    any send failure -- callers are expected to catch and tally these
    per-recipient rather than letting one bad address abort the batch."""

    if not SMTP_USER or not SMTP_PASSWORD:
        raise EmailNotConfigured("SMTP_USER / SMTP_PASSWORD are not configured.")

    subject, body = _build_absence_email(student_name, course_code, course_name, session_date, percentage)

    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, [to_email], msg.as_string())