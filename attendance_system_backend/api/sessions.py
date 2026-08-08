from flask import Blueprint, request, jsonify
from database import get_connection
from api.auth import require_api_key
from datetime import datetime

sessions_bp = Blueprint("sessions", __name__)


# ------------------------
# Start Session
# ------------------------
@sessions_bp.route("/start_session", methods=["POST"])
@require_api_key
def start_session():

    data = request.get_json()

    offering_id = data["offering_id"]

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
        (offering_id,date,start_time,status)

        VALUES(?,?,?,?)

    """,(offering_id,date,time,"Open"))

    conn.commit()

    session_id = cur.lastrowid

    conn.close()

    return jsonify({
        "success":True,
        "session_id":session_id,
        "offering_id":offering_id
    })


# ----------------------------
# Update Session
# ----------------------------
@sessions_bp.route("/sessions/<int:session_id>", methods=["PUT"])
@require_api_key
def update_session(session_id):

    data = request.get_json() or {}

    allowed_fields = ["offering_id", "date", "start_time", "end_time", "status"]
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({"success": False, "error": "No valid fields to update"}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        set_clause = ", ".join(f"{field} = ?" for field in updates)
        values = list(updates.values()) + [session_id]

        cur.execute(f"UPDATE Sessions SET {set_clause} WHERE session_id = ?", values)

        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Session Not Found"}), 404

        conn.commit()

        return jsonify({"success": True, "message": "Session Updated"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()


# ----------------------------
# Delete Session
# ----------------------------
@sessions_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
@require_api_key
def delete_session(session_id):

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM Sessions WHERE session_id = ?", (session_id,))

        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Session Not Found"}), 404

        conn.commit()

        return jsonify({"success": True, "message": "Session Deleted"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()