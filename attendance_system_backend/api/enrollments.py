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




# ----------------------------
# Update Enrollment
# ----------------------------
# NOTE: this is keyed by enrollment_id (the Enrollments primary key), not
# offering_id -- GET /enrollments/<offering_id> above lists enrollments
# *for* an offering, which is a different lookup, so this uses a
# distinct path to avoid any ambiguity between the two IDs.
@enrollments_bp.route("/enrollments/record/<int:enrollment_id>", methods=["PUT"])
@require_api_key
def update_enrollment(enrollment_id):

    data = request.get_json() or {}

    allowed_fields = ["student_id", "offering_id", "status"]
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({"success": False, "error": "No valid fields to update"}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        set_clause = ", ".join(f"{field} = ?" for field in updates)
        values = list(updates.values()) + [enrollment_id]

        cur.execute(
            f"UPDATE Enrollments SET {set_clause} WHERE enrollment_id = ?", values
        )

        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Enrollment Not Found"}), 404

        conn.commit()

        return jsonify({"success": True, "message": "Enrollment Updated"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()


# ----------------------------
# Delete Enrollment
# ----------------------------
@enrollments_bp.route("/enrollments/record/<int:enrollment_id>", methods=["DELETE"])
@require_api_key
def delete_enrollment(enrollment_id):

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM Enrollments WHERE enrollment_id = ?", (enrollment_id,))

        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Enrollment Not Found"}), 404

        conn.commit()

        return jsonify({"success": True, "message": "Enrollment Deleted"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()