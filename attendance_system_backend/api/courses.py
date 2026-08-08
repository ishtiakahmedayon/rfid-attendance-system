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

    conn = get_connection()

    cur = conn.cursor()

    try:

        cur.execute("""

        INSERT INTO Courses
        VALUES(?,?,?)

        """, (course_code, course_name, semester))

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
