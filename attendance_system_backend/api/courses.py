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

@offerings_bp.route("/offerings/<int:offering_id>", methods=["DELETE"])
@require_api_key
def delete_offering(offering_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "DELETE FROM CourseOfferings WHERE offering_id = ?",
            (offering_id,)
        )

        if cur.rowcount == 0:
            return jsonify({
                "success": False,
                "error": "Offering not found"
            }), 404

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Offering deleted"
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    finally:
        conn.close()


@offerings_bp.route("/offerings/<int:offering_id>", methods=["PUT"])
@require_api_key
def update_offering(offering_id):
    data = request.get_json()

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get existing offering
        cur.execute(
            """
            SELECT course_code, academic_year, batch, assigned_teacher_id
            FROM CourseOfferings
            WHERE offering_id = ?
            """,
            (offering_id,)
        )

        existing = cur.fetchone()

        if not existing:
            return jsonify({
                "success": False,
                "error": "Offering not found"
            }), 404

        # Keep existing values if they aren't provided
        course_code = data.get("course_code", existing["course_code"])
        academic_year = data.get("academic_year", existing["academic_year"])
        batch = data.get("batch", existing["batch"])
        assigned_teacher_id = data.get(
            "assigned_teacher_id",
            existing["assigned_teacher_id"]
        )

        cur.execute(
            """
            UPDATE CourseOfferings
            SET course_code = ?,
                academic_year = ?,
                batch = ?,
                assigned_teacher_id = ?
            WHERE offering_id = ?
            """,
            (
                course_code,
                academic_year,
                batch,
                assigned_teacher_id,
                offering_id
            )
        )

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Offering updated",
            "offering_id": offering_id
        })

    except Exception as e:
        conn.rollback()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    finally:
        conn.close()