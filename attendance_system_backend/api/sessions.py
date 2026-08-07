from flask import Blueprint, request, jsonify
from database import get_connection
from datetime import datetime

sessions_bp = Blueprint("sessions", __name__)


# ------------------------
# Start Session
# ------------------------
@sessions_bp.route("/start_session", methods=["POST"])
def start_session():

    data = request.get_json()

    course_code = data["course_code"]

    now = datetime.now()

    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()

    # Close previous open sessions (optional)
    cur.execute("""
        UPDATE Sessions
        SET status='Closed',
            end_time=?
        WHERE status='Open'
    """,(time,))

    cur.execute("""

        INSERT INTO Sessions
        (course_code,date,start_time,status)

        VALUES(?,?,?,?)

    """,(course_code,date,time,"Open"))

    conn.commit()

    session_id = cur.lastrowid

    conn.close()

    return jsonify({
        "success":True,
        "session_id":session_id,
        "course":course_code
    })