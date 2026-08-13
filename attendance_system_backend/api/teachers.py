from flask import Blueprint, jsonify, request

from database import get_connection
from api.auth import require_api_key

teachers_bp = Blueprint("teachers", __name__)


@teachers_bp.route("/teachers", methods=["POST"])
@require_api_key
def add_teacher():
    data = request.get_json()

    teacher_id = data["teacher_id"]
    name = data["name"]
    password = data["password"]
    rfid_uid = data.get("rfid_uid")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO Teachers (teacher_id, name, password, rfid_uid)
            VALUES (?,?,?,?)
            """,
            (teacher_id, name, password, rfid_uid),
        )
        conn.commit()

        return jsonify({"success": True, "message": "Teacher Added"})

    except Exception:
        return jsonify({"success": False, "error": "Failed to add teacher"}), 400

    finally:
        conn.close()


@teachers_bp.route("/teachers", methods=["GET"])
@require_api_key
def get_teachers():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT teacher_id, name, rfid_uid FROM Teachers ORDER BY teacher_id")

    rows = cur.fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])

# ----------------------------
# Update Teacher
# ----------------------------
@teachers_bp.route("/teachers/<teacher_id>", methods=["PUT"])
@require_api_key
def update_teacher(teacher_id):

    data = request.get_json() or {}

    allowed_fields = ["name", "password", "rfid_uid"]
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({"success": False, "error": "No valid fields to update"}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        set_clause = ", ".join(f"{field} = ?" for field in updates)
        values = list(updates.values()) + [teacher_id]

        cur.execute(f"UPDATE Teachers SET {set_clause} WHERE teacher_id = ?", values)

        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Teacher Not Found"}), 404

        conn.commit()

        return jsonify({"success": True, "message": "Teacher Updated"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()


# ----------------------------
# Delete Teacher
# ----------------------------
@teachers_bp.route("/teachers/<teacher_id>", methods=["DELETE"])
@require_api_key
def delete_teacher(teacher_id):

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM Teachers WHERE teacher_id = ?", (teacher_id,))

        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Teacher Not Found"}), 404

        conn.commit()

        return jsonify({"success": True, "message": "Teacher Deleted"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()