from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_connection
from ui import login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Every table an admin can browse read-only, including the two that are
# deliberately NOT editable (Sessions, Attendance) -- system-generated
# records that should only ever be changed through the normal attendance
# flow, never hand-edited.
VIEWABLE_TABLES = [
    "Students",
    "Teachers",
    "Courses",
    "CourseOfferings",
    "Enrollments",
    "Sessions",
    "Attendance",
    "ArchivedOfferings",
    "Admins",
]

# Entities with full Create/Read/Update/Delete via the dashboard.
# Sessions and Attendance are intentionally absent from this dict --
# there are no admin.entity_* routes for them at all, so the exclusion
# is enforced at the routing level, not just hidden in the UI.
ENTITY_META = {
    "students": {"table": "Students", "pk": "student_id", "label": "Student"},
    "teachers": {"table": "Teachers", "pk": "teacher_id", "label": "Teacher"},
    "courses": {"table": "Courses", "pk": "course_code", "label": "Course"},
    "offerings": {"table": "CourseOfferings", "pk": "offering_id", "label": "Course Offering"},
    "enrollments": {"table": "Enrollments", "pk": "enrollment_id", "label": "Enrollment"},
    "admins": {"table": "Admins", "pk": "admin_id", "label": "Admin"},
}


# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT admin_id, username, password FROM Admins WHERE username = ?", (username,))
        admin = cur.fetchone()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session.clear()
            session["role"] = "admin"
            session["admin_id"] = admin["admin_id"]
            session["admin_username"] = admin["username"]
            return redirect(url_for("admin.dashboard"))

        return render_template("admin_login.html", error="Invalid credentials")

    return render_template("admin_login.html", error=None)


@admin_bp.route("/dashboard")
@login_required(role="admin")
def dashboard():
    return render_template(
        "admin_dashboard.html",
        admin_username=session.get("admin_username"),
        entities=ENTITY_META,
        tables=VIEWABLE_TABLES,
    )


# ---------------------------------------------------------------------
# Choice-list helpers (for dropdown fields)
# ---------------------------------------------------------------------

def _teacher_choices(cur):
    cur.execute("SELECT teacher_id, name FROM Teachers ORDER BY name")
    return [(r["teacher_id"], f"{r['name']} ({r['teacher_id']})") for r in cur.fetchall()]


def _course_choices(cur):
    cur.execute("SELECT course_code, course_name FROM Courses ORDER BY course_name")
    return [(r["course_code"], f"{r['course_name']} ({r['course_code']})") for r in cur.fetchall()]


def _student_choices(cur):
    cur.execute("SELECT student_id, name FROM Students ORDER BY name")
    return [(r["student_id"], f"{r['name']} ({r['student_id']})") for r in cur.fetchall()]


def _offering_choices(cur):
    cur.execute(
        """
        SELECT CourseOfferings.offering_id, Courses.course_name, CourseOfferings.academic_year
        FROM CourseOfferings
        JOIN Courses ON Courses.course_code = CourseOfferings.course_code
        ORDER BY CourseOfferings.academic_year DESC, Courses.course_name
        """
    )
    return [
        (r["offering_id"], f"{r['course_name']} — {r['academic_year']} (#{r['offering_id']})")
        for r in cur.fetchall()
    ]


# ---------------------------------------------------------------------
# Field specs -- one function per entity, shared by both the create and
# edit forms. `row` is None for create, a sqlite3.Row for edit.
# ---------------------------------------------------------------------

def _fields_students(cur, row):
    return [
        {"name": "student_id", "label": "Student ID", "type": "readonly" if row else "text",
         "value": row["student_id"] if row else "", "required": True},
        {"name": "name", "label": "Name", "type": "text",
         "value": row["name"] if row else "", "required": True},
        {"name": "batch", "label": "Batch", "type": "text",
         "value": row["batch"] if row else "", "required": False},
        {"name": "rfid_uid", "label": "RFID Card UID", "type": "text",
         "value": row["rfid_uid"] if row else "", "required": False},
    ]


def _fields_teachers(cur, row):
    return [
        {"name": "teacher_id", "label": "Teacher ID", "type": "readonly" if row else "text",
         "value": row["teacher_id"] if row else "", "required": True},
        {"name": "name", "label": "Name", "type": "text",
         "value": row["name"] if row else "", "required": True},
        {"name": "password", "label": "Password", "type": "text",
         "value": row["password"] if row else "", "required": True,
         "hint": "Stored and checked as plain text by the existing teacher login -- not hashed."},
        {"name": "rfid_uid", "label": "RFID Card UID (for device session-start confirmation)",
         "type": "text", "value": row["rfid_uid"] if row else "", "required": False},
    ]


def _fields_courses(cur, row):
    return [
        {"name": "course_code", "label": "Course Code", "type": "readonly" if row else "text",
         "value": row["course_code"] if row else "", "required": True},
        {"name": "course_name", "label": "Course Name", "type": "text",
         "value": row["course_name"] if row else "", "required": True},
        {"name": "semester", "label": "Semester", "type": "text",
         "value": row["semester"] if row else "", "required": False},
        {"name": "credit", "label": "Credit", "type": "number",
         "value": row["credit"] if row else "", "required": False},
    ]


def _fields_offerings(cur, row):
    return [
        {"name": "offering_id", "label": "Offering ID", "type": "readonly",
         "value": row["offering_id"] if row else "(assigned automatically)", "required": False},
        {"name": "course_code", "label": "Course", "type": "select",
         "value": row["course_code"] if row else "", "required": True,
         "options": _course_choices(cur)},
        {"name": "academic_year", "label": "Academic Year", "type": "number",
         "value": row["academic_year"] if row else "", "required": True},
        {"name": "assigned_teacher_id", "label": "Assigned Teacher", "type": "select",
         "value": row["assigned_teacher_id"] if row else "", "required": False,
         "options": _teacher_choices(cur)},
    ]


def _fields_enrollments(cur, row):
    return [
        {"name": "enrollment_id", "label": "Enrollment ID", "type": "readonly",
         "value": row["enrollment_id"] if row else "(assigned automatically)", "required": False},
        {"name": "student_id", "label": "Student", "type": "select",
         "value": row["student_id"] if row else "", "required": True,
         "options": _student_choices(cur)},
        {"name": "offering_id", "label": "Course Offering", "type": "select",
         "value": row["offering_id"] if row else "", "required": True,
         "options": _offering_choices(cur)},
        {"name": "status", "label": "Status", "type": "select",
         "value": row["status"] if row else "Active", "required": True,
         "options": [("Active", "Active"), ("Inactive", "Inactive")]},
    ]


def _fields_admins(cur, row):
    return [
        {"name": "admin_id", "label": "Admin ID", "type": "readonly",
         "value": row["admin_id"] if row else "(assigned automatically)", "required": False},
        {"name": "username", "label": "Username", "type": "text",
         "value": row["username"] if row else "", "required": True},
        {"name": "password", "label": "Password", "type": "password",
         "value": "", "required": not row,
         "hint": "Leave blank to keep the current password." if row else "Will be hashed before storing."},
    ]


FIELD_BUILDERS = {
    "students": _fields_students,
    "teachers": _fields_teachers,
    "courses": _fields_courses,
    "offerings": _fields_offerings,
    "enrollments": _fields_enrollments,
    "admins": _fields_admins,
}


# ---------------------------------------------------------------------
# List-view column specs + row queries (joins in readable names where
# it helps, e.g. showing a teacher's name instead of just their ID).
# ---------------------------------------------------------------------

def _list_students(cur):
    columns = [("student_id", "ID"), ("name", "Name"), ("batch", "Batch"), ("rfid_uid", "Card UID")]
    cur.execute("SELECT student_id, name, batch, rfid_uid FROM Students ORDER BY name")
    return columns, cur.fetchall()


def _list_teachers(cur):
    columns = [("teacher_id", "ID"), ("name", "Name"), ("rfid_uid", "Card UID")]
    cur.execute("SELECT teacher_id, name, rfid_uid FROM Teachers ORDER BY name")
    return columns, cur.fetchall()


def _list_courses(cur):
    columns = [("course_code", "Code"), ("course_name", "Name"), ("semester", "Semester"), ("credit", "Credit")]
    cur.execute("SELECT course_code, course_name, semester, credit FROM Courses ORDER BY course_name")
    return columns, cur.fetchall()


def _list_offerings(cur):
    columns = [("offering_id", "ID"), ("course_name", "Course"), ("academic_year", "Year"), ("teacher_name", "Teacher")]
    cur.execute(
        """
        SELECT
            CourseOfferings.offering_id,
            Courses.course_name,
            CourseOfferings.academic_year,
            Teachers.name AS teacher_name
        FROM CourseOfferings
        JOIN Courses ON Courses.course_code = CourseOfferings.course_code
        LEFT JOIN Teachers ON Teachers.teacher_id = CourseOfferings.assigned_teacher_id
        ORDER BY CourseOfferings.academic_year DESC, Courses.course_name
        """
    )
    return columns, cur.fetchall()


def _list_enrollments(cur):
    columns = [("enrollment_id", "ID"), ("student_name", "Student"), ("course_name", "Course"), ("academic_year", "Year"), ("status", "Status")]
    cur.execute(
        """
        SELECT
            Enrollments.enrollment_id,
            Students.name AS student_name,
            Courses.course_name,
            CourseOfferings.academic_year,
            Enrollments.status
        FROM Enrollments
        JOIN Students ON Students.student_id = Enrollments.student_id
        JOIN CourseOfferings ON CourseOfferings.offering_id = Enrollments.offering_id
        JOIN Courses ON Courses.course_code = CourseOfferings.course_code
        ORDER BY Enrollments.enrollment_id DESC
        """
    )
    return columns, cur.fetchall()


def _list_admins(cur):
    columns = [("admin_id", "ID"), ("username", "Username")]
    cur.execute("SELECT admin_id, username FROM Admins ORDER BY username")
    return columns, cur.fetchall()


LIST_BUILDERS = {
    "students": _list_students,
    "teachers": _list_teachers,
    "courses": _list_courses,
    "offerings": _list_offerings,
    "enrollments": _list_enrollments,
    "admins": _list_admins,
}


# ---------------------------------------------------------------------
# List / New / Edit / Delete -- shared routes, entity-specific logic
# ---------------------------------------------------------------------

@admin_bp.route("/<entity>/")
@login_required(role="admin")
def entity_list(entity):
    if entity not in ENTITY_META:
        return redirect(url_for("admin.dashboard"))

    conn = get_connection()
    cur = conn.cursor()
    columns, rows = LIST_BUILDERS[entity](cur)
    conn.close()

    return render_template(
        "admin_entity_list.html",
        entity=entity,
        entity_label=ENTITY_META[entity]["label"],
        pk_field=ENTITY_META[entity]["pk"],
        columns=columns,
        rows=rows,
    )


@admin_bp.route("/<entity>/new", methods=["GET", "POST"])
@login_required(role="admin")
def entity_new(entity):
    if entity not in ENTITY_META:
        return redirect(url_for("admin.dashboard"))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        error = _save_entity(cur, conn, entity, request.form, row=None)
        if error is None:
            conn.close()
            return redirect(url_for("admin.entity_list", entity=entity))

        fields = FIELD_BUILDERS[entity](cur, None)
        conn.close()
        return render_template(
            "admin_entity_form.html",
            entity=entity,
            entity_label=ENTITY_META[entity]["label"],
            is_edit=False,
            fields=fields,
            error=error,
        )

    fields = FIELD_BUILDERS[entity](cur, None)
    conn.close()
    return render_template(
        "admin_entity_form.html",
        entity=entity,
        entity_label=ENTITY_META[entity]["label"],
        is_edit=False,
        fields=fields,
        error=None,
    )


@admin_bp.route("/<entity>/<pk>/edit", methods=["GET", "POST"])
@login_required(role="admin")
def entity_edit(entity, pk):
    if entity not in ENTITY_META:
        return redirect(url_for("admin.dashboard"))

    meta = ENTITY_META[entity]
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT * FROM {meta['table']} WHERE {meta['pk']} = ?", (pk,))
    row = cur.fetchone()

    if row is None:
        conn.close()
        return redirect(url_for("admin.entity_list", entity=entity))

    if request.method == "POST":
        error = _save_entity(cur, conn, entity, request.form, row=row)
        if error is None:
            conn.close()
            return redirect(url_for("admin.entity_list", entity=entity))

        fields = FIELD_BUILDERS[entity](cur, row)
        conn.close()
        return render_template(
            "admin_entity_form.html",
            entity=entity,
            entity_label=meta["label"],
            is_edit=True,
            fields=fields,
            error=error,
        )

    fields = FIELD_BUILDERS[entity](cur, row)
    conn.close()
    return render_template(
        "admin_entity_form.html",
        entity=entity,
        entity_label=meta["label"],
        is_edit=True,
        fields=fields,
        error=None,
    )


@admin_bp.route("/<entity>/<pk>/delete", methods=["POST"])
@login_required(role="admin")
def entity_delete(entity, pk):
    if entity not in ENTITY_META:
        return redirect(url_for("admin.dashboard"))

    meta = ENTITY_META[entity]
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(f"DELETE FROM {meta['table']} WHERE {meta['pk']} = ?", (pk,))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()

    return redirect(url_for("admin.entity_list", entity=entity))


def _save_entity(cur, conn, entity, form, row):
    """Validates + writes a create/update for one entity. Returns an
    error string on failure, or None on success (already committed)."""

    try:
        if entity == "students":
            student_id = form.get("student_id", "").strip()
            name = form.get("name", "").strip()
            batch = form.get("batch", "").strip() or None
            rfid_uid = form.get("rfid_uid", "").strip() or None

            if row is None:
                cur.execute(
                    "INSERT INTO Students (student_id, name, batch, rfid_uid) VALUES (?,?,?,?)",
                    (student_id, name, batch, rfid_uid),
                )
            else:
                cur.execute(
                    "UPDATE Students SET name=?, batch=?, rfid_uid=? WHERE student_id=?",
                    (name, batch, rfid_uid, row["student_id"]),
                )

        elif entity == "teachers":
            teacher_id = form.get("teacher_id", "").strip()
            name = form.get("name", "").strip()
            password = form.get("password", "").strip()
            rfid_uid = form.get("rfid_uid", "").strip() or None

            if row is None:
                cur.execute(
                    "INSERT INTO Teachers (teacher_id, name, password, rfid_uid) VALUES (?,?,?,?)",
                    (teacher_id, name, password, rfid_uid),
                )
            else:
                cur.execute(
                    "UPDATE Teachers SET name=?, password=?, rfid_uid=? WHERE teacher_id=?",
                    (name, password, rfid_uid, row["teacher_id"]),
                )

        elif entity == "courses":
            course_code = form.get("course_code", "").strip()
            course_name = form.get("course_name", "").strip()
            semester = form.get("semester", "").strip() or None
            credit = form.get("credit", "").strip() or None

            if row is None:
                cur.execute(
                    "INSERT INTO Courses (course_code, course_name, semester, credit) VALUES (?,?,?,?)",
                    (course_code, course_name, semester, credit),
                )
            else:
                cur.execute(
                    "UPDATE Courses SET course_name=?, semester=?, credit=? WHERE course_code=?",
                    (course_name, semester, credit, row["course_code"]),
                )

        elif entity == "offerings":
            course_code = form.get("course_code", "").strip()
            academic_year = form.get("academic_year", "").strip()
            assigned_teacher_id = form.get("assigned_teacher_id", "").strip() or None

            if row is None:
                cur.execute(
                    "INSERT INTO CourseOfferings (course_code, academic_year, assigned_teacher_id) VALUES (?,?,?)",
                    (course_code, academic_year, assigned_teacher_id),
                )
            else:
                cur.execute(
                    "UPDATE CourseOfferings SET course_code=?, academic_year=?, assigned_teacher_id=? WHERE offering_id=?",
                    (course_code, academic_year, assigned_teacher_id, row["offering_id"]),
                )

        elif entity == "enrollments":
            student_id = form.get("student_id", "").strip()
            offering_id = form.get("offering_id", "").strip()
            status = form.get("status", "").strip()

            if row is None:
                cur.execute(
                    "INSERT INTO Enrollments (student_id, offering_id, status) VALUES (?,?,?)",
                    (student_id, offering_id, status),
                )
            else:
                cur.execute(
                    "UPDATE Enrollments SET student_id=?, offering_id=?, status=? WHERE enrollment_id=?",
                    (student_id, offering_id, status, row["enrollment_id"]),
                )

        elif entity == "admins":
            username = form.get("username", "").strip()
            password = form.get("password", "").strip()

            if row is None:
                if not password:
                    return "Password is required for a new admin."
                cur.execute(
                    "INSERT INTO Admins (username, password) VALUES (?,?)",
                    (username, generate_password_hash(password)),
                )
            else:
                if password:
                    cur.execute(
                        "UPDATE Admins SET username=?, password=? WHERE admin_id=?",
                        (username, generate_password_hash(password), row["admin_id"]),
                    )
                else:
                    cur.execute(
                        "UPDATE Admins SET username=? WHERE admin_id=?",
                        (username, row["admin_id"]),
                    )

        conn.commit()
        return None

    except Exception as e:
        conn.rollback()
        return f"Could not save: {e}"


# ---------------------------------------------------------------------
# Read-only DB viewer -- every table, including Sessions/Attendance,
# but with no edit/delete routes ever defined for those two.
# ---------------------------------------------------------------------

@admin_bp.route("/db/")
@login_required(role="admin")
def db_index():
    return render_template("admin_db_viewer.html", tables=VIEWABLE_TABLES, table=None, columns=None, rows=None)


@admin_bp.route("/db/<table>")
@login_required(role="admin")
def db_view(table):
    if table not in VIEWABLE_TABLES:
        return redirect(url_for("admin.db_index"))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    columns = rows[0].keys() if rows else [d[1] for d in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    conn.close()

    return render_template(
        "admin_db_viewer.html", tables=VIEWABLE_TABLES, table=table, columns=columns, rows=rows
    )