from flask import Blueprint, request, jsonify
from database import get_connection
from api.auth import require_api_key

students_bp = Blueprint("students", __name__)

# ----------------------------
# Add Student
# ----------------------------
@students_bp.route("/students", methods=["POST"])
@require_api_key
def add_student():

    data = request.get_json()

    student_id = data["student_id"]
    name = data["name"]
    batch = data["batch"]
    rfid_uid = data["rfid_uid"]

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            INSERT INTO Students
            VALUES(?,?,?,?)
        """, (student_id, name, batch, rfid_uid))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Student Added"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    finally:
        conn.close()


# ----------------------------
# View Students
# ----------------------------
@students_bp.route("/students", methods=["GET"])
@require_api_key
def get_students():

    conn = get_connection()

    cur = conn.cursor()

    cur.execute("SELECT * FROM Students ORDER BY student_id")

    rows = cur.fetchall()

    conn.close()

    students = []

    for row in rows:
        students.append(dict(row))

    return jsonify(students)



# ----------------------------
# Update Student
# ----------------------------
@students_bp.route("/students/<student_id>", methods=["PUT"])
@require_api_key
def update_student(student_id):

    data = request.get_json() or {}

    allowed_fields = ["name", "batch", "rfid_uid"]
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({"success": False, "error": "No valid fields to update"}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        set_clause = ", ".join(f"{field} = ?" for field in updates)
        values = list(updates.values()) + [student_id]

        cur.execute(f"UPDATE Students SET {set_clause} WHERE student_id = ?", values)

        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Student Not Found"}), 404

        conn.commit()

        return jsonify({"success": True, "message": "Student Updated"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()


# ----------------------------
# Delete Student
# ----------------------------
@students_bp.route("/students/<student_id>", methods=["DELETE"])
@require_api_key
def delete_student(student_id):

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM Students WHERE student_id = ?", (student_id,))

        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Student Not Found"}), 404

        conn.commit()

        return jsonify({"success": True, "message": "Student Deleted"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()
