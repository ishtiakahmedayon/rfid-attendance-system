from flask import Blueprint, jsonify, request

from database import get_connection
from api.auth import require_api_key

device_bp = Blueprint("device", __name__)


@device_bp.route("/device_command")
@require_api_key
def device_command():
    """Tells the ESP32 what it should be doing right now.

    This is level-triggered, not event-triggered: it always reports the
    currently Open session (if any), rather than a one-shot "start now"
    command. That way a missed poll just gets picked up on the next
    poll a few seconds later instead of losing the instruction -- the
    device just keeps asking "what should I be doing?" and the server
    always answers based on current DB state.

    Only one session can be Open at a time (enforced when a session is
    started), which matches there being a single physical device today.
    """

    conn = get_connection()
    cur = conn.cursor()

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
    open_session = cur.fetchone()
    conn.close()

    if open_session is None:
        return jsonify({"active": False})

    return jsonify(
        {
            "active": True,
            "session_id": open_session["session_id"],
            "offering_id": open_session["offering_id"],
            "course_code": open_session["course_code"],
        }
    )


@device_bp.route("/verify_teacher_card", methods=["POST"])
@require_api_key
def verify_teacher_card():
    """Checks a scanned card UID against the *specific* teacher assigned
    to the given offering, before the device is allowed to start a
    session for it.

    Deliberately scoped to "does this UID belong to the offering's own
    assigned teacher" rather than "does this UID belong to any teacher"
    -- otherwise any teacher's card could start any course's session.

    Returns only a match boolean (plus the offering_id for the device
    to echo back) -- no teacher identity is exposed to the device beyond
    that yes/no.
    """

    data = request.get_json() or {}
    uid = (data.get("uid") or "").strip()
    offering_id = data.get("offering_id")

    if not uid or not offering_id:
        return jsonify({"success": False, "message": "uid and offering_id are required"}), 400

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT Teachers.rfid_uid
        FROM CourseOfferings
        JOIN Teachers ON Teachers.teacher_id = CourseOfferings.assigned_teacher_id
        WHERE CourseOfferings.offering_id = ?
        """,
        (offering_id,),
    )
    row = cur.fetchone()
    conn.close()

    assigned_uid = row["rfid_uid"] if row else None
    match = bool(assigned_uid) and assigned_uid == uid

    return jsonify({"success": True, "match": match, "offering_id": offering_id})