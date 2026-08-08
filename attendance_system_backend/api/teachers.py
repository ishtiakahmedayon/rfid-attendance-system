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

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO Teachers (teacher_id, name, password)
            VALUES (?,?,?)
            """,
            (teacher_id, name, password),
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

    cur.execute("SELECT teacher_id, name FROM Teachers ORDER BY teacher_id")

    rows = cur.fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])