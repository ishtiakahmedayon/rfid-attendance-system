from flask import Flask, redirect, session, url_for

from config import DEBUG, HOST, PORT, SECRET_KEY
from api.students import students_bp
from api.courses import courses_bp
from api.sessions import sessions_bp
from api.attendance import attendance_bp
from api.offerings import offerings_bp
from api.enrollments import enrollments_bp
from api.teachers import teachers_bp
from api.device import device_bp
from ui import ui_bp

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

app.register_blueprint(students_bp)
app.register_blueprint(courses_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(offerings_bp)
app.register_blueprint(enrollments_bp)
app.register_blueprint(teachers_bp)
app.register_blueprint(device_bp)
app.register_blueprint(ui_bp)


@app.route("/")
def home():
    if session.get("role") == "teacher":
        return redirect(url_for("ui.teacher_dashboard"))
    if session.get("role") == "student":
        return redirect(url_for("ui.student_dashboard"))
    return redirect(url_for("ui.login"))


@app.route("/health")
def health():
    return {"status": "running"}


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)