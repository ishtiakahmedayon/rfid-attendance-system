import json
import logging
import urllib.error
import urllib.request

from config import RESEND_API_KEY, RESEND_FROM_EMAIL, RESEND_FROM_NAME

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailNotConfigured(Exception):
    """Raised when RESEND_API_KEY isn't set."""


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
    """Sends one absence-notification email via the Resend HTTP API.

    Raises EmailNotConfigured if RESEND_API_KEY isn't set, or a plain
    Exception on any send failure (bad response, network error) --
    callers are expected to catch and tally these per-recipient rather
    than letting one bad address abort the batch.

    Uses a plain HTTPS POST (via urllib, no extra dependency) instead
    of raw SMTP -- see the comment in config.py for why: some hosts
    block outbound SMTP ports entirely, which used to make this call
    hang indefinitely.
    """

    if not RESEND_API_KEY:
        raise EmailNotConfigured("RESEND_API_KEY is not configured.")

    subject, body = _build_absence_email(student_name, course_code, course_name, session_date, percentage)

    payload = {
        "from": f"{RESEND_FROM_NAME} <{RESEND_FROM_EMAIL}>",
        "to": [to_email],
        "subject": subject,
        "text": body,
    }

    request = urllib.request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status >= 300:
                raise Exception(f"Resend API returned status {response.status}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise Exception(f"Resend API error {e.code}: {error_body}") from e
    except urllib.error.URLError as e:
        raise Exception(f"Could not reach Resend API: {e.reason}") from e