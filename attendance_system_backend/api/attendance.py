from flask import Blueprint, request, jsonify
from database import get_connection
from datetime import datetime

attendance_bp = Blueprint("attendance", __name__)
@attendance_bp.route("/scan", methods=["POST"])
def scan():

    data = request.get_json()

    session_id = data["session_id"]
    uid = data["uid"]

    conn = get_connection()
    cur = conn.cursor()

    # Find student

    cur.execute("""

    SELECT student_id,name

    FROM Students

    WHERE rfid_uid=?

    """,(uid,))

    student = cur.fetchone()

    if student is None:

        conn.close()

        return jsonify({
            "success":False,
            "message":"Unknown Card"
        })

    student_id = student["student_id"]

    name = student["name"]

    # Duplicate check

    cur.execute("""

    SELECT *

    FROM Attendance

    WHERE session_id=?

    AND student_id=?

    """,(session_id,student_id))

    if cur.fetchone():

        conn.close()

        return jsonify({
            "success":False,
            "message":"Already Present"
        })

    now = datetime.now()

    time = now.strftime("%H:%M:%S")

    cur.execute("""

    INSERT INTO Attendance

    (session_id,student_id,scan_time,status)

    VALUES(?,?,?,?)

    """,(session_id,student_id,time,"Present"))

    conn.commit()

    conn.close()

    return jsonify({

        "success":True,

        "student":name,

        "status":"Present"

    })

@attendance_bp.route("/attendance/<int:session_id>")
def attendance(session_id):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute("""

    SELECT

    Students.student_id,

    Students.name,

    Attendance.scan_time,

    Attendance.status

    FROM Attendance

    JOIN Students

    ON Attendance.student_id = Students.student_id

    WHERE Attendance.session_id=?

    ORDER BY Students.name

    """,(session_id,))

    rows = cur.fetchall()

    conn.close()

    result=[]

    for row in rows:

        result.append(dict(row))

    return jsonify(result)


@attendance_bp.route("/end_session", methods=["POST"])
def end_session():

    data = request.get_json()

    session_id = data["session_id"]

    conn = get_connection()

    cur = conn.cursor()

    time = datetime.now().strftime("%H:%M:%S")

    cur.execute("""

    UPDATE Sessions

    SET

    status='Closed',

    end_time=?

    WHERE session_id=?

    """,(time,session_id))

    conn.commit()

    conn.close()

    return jsonify({

        "success":True,

        "message":"Session Closed"

    })