from flask import Blueprint, request, jsonify
from database import get_connection

offerings_bp = Blueprint("offerings", __name__)


@offerings_bp.route("/offerings", methods=["POST"])
def add_offering():

    data = request.get_json()

    course_code = data["course_code"]
    academic_year = data["academic_year"]
    batch = data["batch"]

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO CourseOfferings (course_code, academic_year, batch)
            VALUES (?,?,?)
        """, (course_code, academic_year, batch))

        conn.commit()

        return jsonify({
            "success": True,
            "offering_id": cur.lastrowid
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    finally:
        conn.close()


@offerings_bp.route("/offerings", methods=["GET"])
def get_offerings():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            CourseOfferings.offering_id,
            CourseOfferings.course_code,
            Courses.course_name,
            CourseOfferings.academic_year,
            CourseOfferings.batch
        FROM CourseOfferings
        JOIN Courses ON CourseOfferings.course_code = Courses.course_code
        ORDER BY CourseOfferings.academic_year DESC, CourseOfferings.offering_id
    """)

    rows = cur.fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])


@offerings_bp.route("/offerings/<int:offering_id>")
def get_offering(offering_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            CourseOfferings.offering_id,
            CourseOfferings.course_code,
            Courses.course_name,
            CourseOfferings.academic_year,
            CourseOfferings.batch
        FROM CourseOfferings
        JOIN Courses ON CourseOfferings.course_code = Courses.course_code
        WHERE CourseOfferings.offering_id = ?
    """, (offering_id,))

    row = cur.fetchone()
    conn.close()

    if row is None:
        return jsonify({"success": False, "message": "Offering Not Found"}), 404

    return jsonify(dict(row))
