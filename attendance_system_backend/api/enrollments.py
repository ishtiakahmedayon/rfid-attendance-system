from flask import Blueprint, request, jsonify
from database import get_connection
from api.auth import require_api_key

enrollments_bp = Blueprint("enrollments", __name__)


@enrollments_bp.route("/enroll", methods=["POST"])
@require_api_key
def enroll_student():

    data = request.get_json()

    student_id = data["student_id"]
    offering_id = data["offering_id"]

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO Enrollments (student_id, offering_id, status)
            VALUES (?,?,'Active')
        """, (student_id, offering_id))

        conn.commit()

        return jsonify({"success": True, "message": "Enrolled"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()


@enrollments_bp.route("/enrollments/<int:offering_id>")
@require_api_key
def get_enrollments(offering_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT Students.student_id, Students.name, Enrollments.status
        FROM Enrollments
        JOIN Students ON Enrollments.student_id = Students.student_id
        WHERE Enrollments.offering_id = ?
        ORDER BY Students.name
    """, (offering_id,))

    rows = cur.fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])