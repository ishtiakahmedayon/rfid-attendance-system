from flask import Flask

from config import HOST, PORT

from flask import Flask

from api.students import students_bp
from api.courses import courses_bp
from api.sessions import sessions_bp
from api.attendance import attendance_bp
from api.offerings import offerings_bp
from api.enrollments import enrollments_bp

app = Flask(__name__)

app.register_blueprint(students_bp)
app.register_blueprint(courses_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(offerings_bp)
app.register_blueprint(enrollments_bp)





@app.route("/")
def home():

    return """
    <h2>RFID Attendance Server</h2>
    <h3>Server Running</h3>
    """


@app.route("/health")
def health():

    return {
        "status": "running"
    }


if __name__ == "__main__":

    app.run(
        host=HOST,
        port=PORT,
        debug=True
    )