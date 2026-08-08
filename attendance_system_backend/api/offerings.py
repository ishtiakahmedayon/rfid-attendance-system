from flask import Blueprint, request, jsonify
from database import get_connection
from api.auth import require_api_key

offerings_bp = Blueprint("offerings", __name__)


@offerings_bp.route("/offerings", methods=["POST"])
@require_api_key
def add_offering():

    data = request.get_json()

    course_code = data["course_code"]
    academic_year = data["academic_year"]
    batch = data["batch"]
    assigned_teacher_id = data.get("assigned_teacher_id")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO CourseOfferings (course_code, academic_year, batch, assigned_teacher_id)
            VALUES (?,?,?,?)
        """,
            (course_code, academic_year, batch, assigned_teacher_id),
        )

        conn.commit()

        return jsonify({"success": True, "offering_id": cur.lastrowid})

    except Exception:
        return jsonify({"success": False, "error": "Failed to add offering"}), 400

    finally:
        conn.close()


@offerings_bp.route("/offerings", methods=["GET"])
@require_api_key
def get_offerings():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            CourseOfferings.offering_id,
            CourseOfferings.course_code,
            Courses.course_name,
            CourseOfferings.academic_year,
            CourseOfferings.batch,
            CourseOfferings.assigned_teacher_id,
            Teachers.name AS assigned_teacher_name
        FROM CourseOfferings
        JOIN Courses ON CourseOfferings.course_code = Courses.course_code
        LEFT JOIN Teachers ON CourseOfferings.assigned_teacher_id = Teachers.teacher_id
        ORDER BY CourseOfferings.academic_year DESC, CourseOfferings.offering_id
    """
    )

    rows = cur.fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])


@offerings_bp.route("/offerings/<int:offering_id>")
@require_api_key
def get_offering(offering_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            CourseOfferings.offering_id,
            CourseOfferings.course_code,
            Courses.course_name,
            CourseOfferings.academic_year,
            CourseOfferings.batch,
            CourseOfferings.assigned_teacher_id,
            Teachers.name AS assigned_teacher_name
        FROM CourseOfferings
        JOIN Courses ON CourseOfferings.course_code = Courses.course_code
        LEFT JOIN Teachers ON CourseOfferings.assigned_teacher_id = Teachers.teacher_id
        WHERE CourseOfferings.offering_id = ?
    """,
        (offering_id,),
    )

    row = cur.fetchone()
    conn.close()

    if row is None:
        return jsonify({"success": False, "message": "Offering Not Found"}), 404

    return jsonify(dict(row))