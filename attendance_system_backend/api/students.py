from flask import Blueprint, request, jsonify
from database import get_connection

students_bp = Blueprint("students", __name__)

# ----------------------------
# Add Student
# ----------------------------
@students_bp.route("/students", methods=["POST"])
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