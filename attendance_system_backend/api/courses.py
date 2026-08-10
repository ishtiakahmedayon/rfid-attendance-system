from flask import Blueprint, request, jsonify
from database import get_connection
from api.auth import require_api_key

courses_bp = Blueprint("courses", __name__)

# ----------------------------
# Add Course
# ----------------------------
@courses_bp.route("/courses", methods=["POST"])
@require_api_key
def add_course():

    data = request.get_json()

    course_code = data["course_code"]
    course_name = data["course_name"]
    semester = data["semester"]
    credit = data.get("credit")

    conn = get_connection()

    cur = conn.cursor()

    try:

        cur.execute("""

        INSERT INTO Courses (course_code, course_name, semester, credit)
        VALUES(?,?,?,?)

        """, (course_code, course_name, semester, credit))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Course Added"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    finally:

        conn.close()


# ----------------------------
# View Courses
# ----------------------------
@courses_bp.route("/courses", methods=["GET"])
@require_api_key
def get_courses():

    conn = get_connection()

    cur = conn.cursor()

    cur.execute("SELECT * FROM Courses ORDER BY course_code")

    rows = cur.fetchall()

    conn.close()

    courses = []

    for row in rows:

        courses.append(dict(row))

    return jsonify(courses)

# ----------------------------
# Update Course
# ----------------------------
@courses_bp.route("/courses/<course_code>", methods=["PUT"])
@require_api_key
def update_course(course_code):

    data = request.get_json() or {}

    allowed_fields = ["course_name", "semester", "credit"]
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({"success": False, "error": "No valid fields to update"}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        set_clause = ", ".join(f"{field} = ?" for field in updates)
        values = list(updates.values()) + [course_code]

        cur.execute(f"UPDATE Courses SET {set_clause} WHERE course_code = ?", values)

        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Course Not Found"}), 404

        conn.commit()

        return jsonify({"success": True, "message": "Course Updated"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()


# ----------------------------
# Delete Course
# ----------------------------
@courses_bp.route("/courses/<course_code>", methods=["DELETE"])
@require_api_key
def delete_course(course_code):

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM Courses WHERE course_code = ?", (course_code,))

        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Course Not Found"}), 404

        conn.commit()

        return jsonify({"success": True, "message": "Course Deleted"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()