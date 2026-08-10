
# RFID Attendance System — Project Summary

An automated classroom attendance system built around an **ESP32 microcontroller with a PN532 RFID reader**, paired with a **Flask + SQLite backend** that provides both a JSON API (for the device) and a browser dashboard (for teachers and students).

A teacher starts a class session either from the web dashboard or from the physical device's menu. Students then tap their RFID card on the reader, and each tap is validated and logged against the session in real time. Both sides — teacher and student — can view live and historical attendance through simple web dashboards.

---

## 1. High-Level Architecture

```
┌─────────────────┐        Wi-Fi / HTTPS           ┌───────────────────────────┐
│   ESP32 + PN532  │ ────────────────────────────▶│   Flask backend (Render)  │
│  (rfid_esp32.ino)│◀──────────────────────────── │  REST API + Web Dashboard │
└─────────────────┘        JSON over HTTP          └─────────────┬────────────┘
        │  OLED display, buzzer, buttons                          │
        │  reads card UID → POSTs /scan                           ▼
        │  polls /device_command every ~3.5s                   ┌───────────────┐
        │  starts/ends sessions                                │ SQLite DB     │
                                                               │(attendance.db)|
                                                               └───────────────┘
                                                                     ▲
                                                                     │
                                                        ┌────────────┴─────────────┐
                                                        │   Browser (Teacher /     │
                                                        │   Student Dashboard)     │
                                                        └──────────────────────────┘
```

The device and the web dashboard are two independent, symmetric ways of starting/stopping a class session — the backend is the single source of truth, and both clients simply poll or push against it.

---

## 2. Repository Structure

```
rfid-attendance-system-updated/
│
├── Readme.MD                          # Original 1-paragraph readme + ER sketch
│
├── attendance_system_backend/         # Flask web application
│   ├── app.py                         # App factory: registers all blueprints, "/" role router, /health
│   ├── config.py                      # Env-driven settings (DB path, host, port, SECRET_KEY, DEVICE_API_KEY)
│   ├── database.py                    # sqlite3 connection helper (row_factory = sqlite3.Row)
│   ├── init_db.py                     # CREATE TABLE script — builds the schema from scratch
│   ├── attendance.db                  # Live SQLite database file (already ahead of init_db.py — see §6)
│   ├── ui.py                          # Session-based web dashboard routes (teacher + student views)
│   ├── requirements.txt               # Flask, gunicorn, and their direct dependencies
│   ├── Procfile                       # `web: gunicorn app:app` — Render/Heroku-style deployment
│   │
│   ├── templates/                     # Jinja2 HTML templates
│   │   ├── login.html                 # Single login form for both teachers and students
│   │   ├── teacher_dashboard.html     # Tab-based course view, session controls, roster, archive menu
│   │   └── student_dashboard.html     # Per-course attendance %, session-by-session history
│   │
│   ├── static/
│   │   └── styles.css                 # All dashboard/login styling
│   │
│   └── api/                           # JSON REST API — one blueprint per resource, all key-protected
│       ├── auth.py                    # require_api_key decorator (shared-secret X-API-Key header)
│       ├── students.py                # CRUD: /students
│       ├── teachers.py                # CRUD: /teachers
│       ├── courses.py                 # CRUD: /courses
│       ├── offerings.py               # CRUD: /offerings (a course taught in a given year)
│       ├── enrollments.py             # CRUD: /enroll, /enrollments/<offering_id>, /enrollments/record/<id>
│       ├── sessions.py                # /start_session, update/delete /sessions/<id>
│       ├── attendance.py              # /scan, /attendance/<session_id>, /end_session
│       └── device.py                  # /device_command — tells the ESP32 what session is currently open
│
└── rfid_esp32/                        # Arduino sketch (multi-tab .ino project)
    ├── rfid_esp32.ino                 # Main file: setup(), loop(), menu state machine, Wi-Fi/OLED/PN532 init
    ├── pollCommand.ino                # GET /device_command — level-triggered session polling
    ├── fetchofferings.ino             # GET /offerings — populates the on-device course-selection menu
    ├── createSession.ino              # POST /start_session — starts a session from the device menu
    ├── endSession.ino                 # POST /end_session — ends a session from the device menu
    ├── sendAttendance.ino             # POST /scan — sends a scanned card's UID + session ID
    ├── readcard.ino                   # Core PN532 UID-read loop (button-interruptible, with poll timeout)
    └── readuidtest.ino                # Standalone "Read Card Test" menu for debugging card reads
```

---

## 3. Data Model

Relationships (see `Readme.MD`'s ER sketch, expanded here with all tables actually present in `attendance.db`):

```
Teachers ──┐
           ├──▶ CourseOfferings ──▶ Sessions ──▶ Attendance ◀── Students
Courses  ──┘         │                                            ▲
                     └──▶ Enrollments ─────────────────────────────┘
                     └──▶ ArchivedOfferings
```

| Table | Key columns | Purpose |
|---|---|---|
| **Students** | `student_id` (PK), `name`, `batch`, `rfid_uid` (unique) | One row per student; `rfid_uid` links a physical card to a student. |
| **Teachers** | `teacher_id` (PK), `name`, `password` | Plaintext-password login for teachers. |
| **Courses** | `course_code` (PK), `course_name`, `semester`, `credit` | A course catalog entry, independent of any specific year. |
| **CourseOfferings** | `offering_id` (PK), `course_code`, `academic_year`, `assigned_teacher_id` | A specific instance of a course being taught in a given year, by a given teacher. `UNIQUE(course_code, academic_year)`. |
| **Enrollments** | `enrollment_id` (PK), `student_id`, `offering_id`, `status` | Links a student to an offering; `status` is `'Active'` (or otherwise, for withdrawn students). `UNIQUE(student_id, offering_id)`. |
| **Sessions** | `session_id` (PK), `offering_id`, `date`, `start_time`, `end_time`, `status` | A single class meeting. `status` is `'Open'` or `'Closed'`. Only **one** session system-wide can be `Open` at a time. |
| **Attendance** | `attendance_id` (PK), `session_id`, `student_id`, `scan_time`, `status` | One row per successful card tap for a session. |
| **ArchivedOfferings** | `offering_id` (PK/FK), `archived_at`, `archived_by` | Lets a teacher "retire" a finished offering so it disappears from both dashboards without deleting data. |

---

## 4. Backend (`attendance_system_backend/`)

### 4.1 App bootstrap (`app.py`)
- Creates the Flask app, loads `SECRET_KEY` from `config.py`.
- Registers 9 blueprints: `students`, `courses`, `sessions`, `attendance`, `offerings`, `enrollments`, `teachers`, `device`, `ui`.
- `/` redirects based on `session["role"]` → teacher dashboard, student dashboard, or login.
- `/health` returns `{"status": "running"}` for uptime checks (used by Render).

### 4.2 Configuration (`config.py`)
All settings are environment-driven with local-dev fallbacks:
- `DATABASE` — path to the SQLite file.
- `HOST` / `PORT` / `DEBUG`
- `SECRET_KEY` — Flask session signing key.
- `DEVICE_API_KEY` — shared secret the ESP32 (and any API caller) must send as `X-API-Key`. Defaults to `"dev-only-change-me"` if unset (⚠️ see §6).

### 4.3 REST API (`api/`) — device- and admin-facing
Every route in this package is wrapped in `@require_api_key` (`api/auth.py`), which checks the `X-API-Key` header against `DEVICE_API_KEY`. This is a single shared secret, not per-user auth — it just keeps the API from being open to the public internet.

| Blueprint | Endpoints | Notes |
|---|---|---|
| `students.py` | `POST/GET /students`, `PUT/DELETE /students/<id>` | Full CRUD; `rfid_uid` must be unique. |
| `teachers.py` | `POST/GET /teachers`, `PUT/DELETE /teachers/<id>` | GET only returns `teacher_id`/`name` (never password). |
| `courses.py` | `POST/GET /courses`, `PUT/DELETE /courses/<code>` | |
| `offerings.py` | `POST/GET /offerings`, `GET/PUT/DELETE /offerings/<id>` | Joins in `course_name` and `assigned_teacher_name` for convenience. |
| `enrollments.py` | `POST /enroll`, `GET /enrollments/<offering_id>`, `PUT/DELETE /enrollments/record/<enrollment_id>` | Deliberately uses a distinct `/record/<id>` path for update/delete to avoid ambiguity with the offering-scoped GET. |
| `sessions.py` | `POST /start_session`, `PUT/DELETE /sessions/<id>` | Starting a session auto-closes any other currently `Open` session. |
| `attendance.py` | `POST /scan`, `GET /attendance/<session_id>`, `POST /end_session` | Core attendance logic — see §4.4. |
| `device.py` | `GET /device_command` | Tells the ESP32 which session (if any) is currently open — see §4.4. |

### 4.4 Core attendance logic
**`POST /scan`** (called by the device on every card tap) validates, in order:
1. The `uid` matches a known student (`Students.rfid_uid`) → else `"Unknown Card"`.
2. The `session_id` exists → else `"Invalid Session"`.
3. The student has an **Active** enrollment in that session's offering → else `"Not Enrolled"`.
4. The student hasn't already been marked present for this session → else `"Already Present"`.

If all checks pass, an `Attendance` row is inserted with the current time and `status = "Present"`.

**`GET /device_command`** is intentionally **level-triggered, not event-triggered**: instead of pushing a one-shot "start now" command, it always reports whichever session is currently `Open` in the DB. This means a missed poll is self-correcting — the device just asks again a few seconds later and gets the current truth, rather than losing an instruction. This directly matches there being a single physical reader device today (only one session can be open system-wide).

### 4.5 Web dashboard (`ui.py`)
Session-cookie-based (Flask `session`), not JWT/token-based. Two roles:

- **Login** (`/login`): a single form tries the submitted username/password first against `Teachers` (teacher_id + password), then against `Students` (student_id + **full name as the password**) if that fails. ⚠️ See §6 for the security implication.
- **Teacher dashboard** (`/teacher/dashboard`):
  - Tab bar of the teacher's own `CourseOfferings` (excluding archived ones).
  - Per-offering: full session history with present/absent counts and per-student status; plus a "class overview" roster showing every enrolled student's overall attendance % across all sessions, color-coded (`red` <60%, `warn` 60–80%, `good` ≥80%).
  - Session controls: **Start**, **Stop**, and **Cancel** (Cancel fully deletes the session and its attendance rows — used for accidental starts; Stop just closes it and keeps the record).
  - Because only one physical device exists, the dashboard also detects and displays whether a session is open *for this course* vs. open *elsewhere* (a different course), disabling Start accordingly.
  - **Archive / Unarchive**: a teacher can archive a finished offering (blocked if it has a live open session); archived offerings move to a separate panel and disappear from the tab bar and from the student's dashboard.
- **Student dashboard** (`/student/dashboard`):
  - One card per enrolled (non-archived) course offering, showing present/absent counts, attendance %, and the same red/warn/good color coding.
  - Full session-by-session history (date, time, present/absent) per course.
  - Courses with zero sessions held yet show a neutral "none" state rather than a misleading 0%.

### 4.6 Database bootstrap
- `init_db.py` runs `CREATE TABLE IF NOT EXISTS` for the core 6 tables.
- The shipped `attendance.db` already contains a 7th table, `ArchivedOfferings`, and the `credit` column on `Courses`, neither of which is created by the two scripts above (see §6).

---

## 5. Firmware (`rfid_esp32/`)

A single Arduino sketch split across multiple tab files (Arduino IDE concatenates `rfid_esp32.ino` first, then the rest alphabetically — this is why shared `#define`s live in the main file).

### 5.1 Hardware
- **ESP32** microcontroller, Wi-Fi enabled.
- **PN532** NFC/RFID reader (I2C, IRQ pin 4, RESET pin 5).
- **SSD1306 OLED** display, 128×64, I2C (SDA 21 / SCL 22).
- Buzzer (pin 25) and status LED (pin 2) for scan feedback.
- Two push buttons: `BTN_NEXT` (32) and `BTN_SELECT` (33) for on-device menu navigation.

### 5.2 Main state machine (`rfid_esp32.ino`)
- `setup()`: initializes buttons/LED/buzzer, I2C, OLED, connects to Wi-Fi, initializes the PN532 (halts with an error screen if not found), then draws the main menu.
- `loop()`:
  1. Every `POLL_INTERVAL_MS` (3.5s), calls `checkForRemoteStart()` — if the server reports a newly opened session (started from the teacher's web dashboard), the device jumps straight into attendance-taking without any menu interaction.
  2. Otherwise redraws the idle main menu (`Create Session`, `Read Card Test`) and responds to button presses.
- **Main menu options**:
  - *Create Session* → `offeringMenu()`: fetches the teacher's course offerings from the server, lets the user scroll/select one (3 rows visible at a time on the small OLED, with an "Exit" option), then `createSession()` posts to `/start_session` and drops into `readCardMenu()`.
  - *Read Card Test* → `readCardMenuTest()`: a standalone debug loop that reads and displays card UIDs without touching any session/attendance state.
- **`readCardMenu()`** (the live attendance-taking loop):
  - Displays "Tap card..." and polls for a card read with a timeout equal to the poll interval (so it can also periodically re-check the server).
  - On each successful scan, calls `sendAttendance()` (`/scan`) and keeps looping.
  - On a poll timeout with no card, re-checks `/device_command` — if the session was ended or changed remotely (e.g., teacher clicked "Stop" on the dashboard), the device exits back to the main menu automatically.
  - Pressing `BTN_NEXT` manually ends the session (posts to `/end_session`) and returns to the menu.

### 5.3 Networking helper pattern (shared across all `.ino` files that talk to the server)
Each HTTP call (`createSession`, `endSession`, `fetchOfferings`, `sendAttendance`, `pollDeviceCommand`) follows the same pattern:
- Up to `HTTP_RETRIES` (3) attempts with increasing backoff.
- `WiFiClientSecure` with `setInsecure()` (TLS without certificate verification).
- `X-API-Key` header set to the hardcoded `API_KEY`.
- Logs the HTTP status code and payload to `Serial` for debugging.

### 5.4 Design notes baked into the firmware
- `pollDeviceCommand()` treats a **failed request** as "no information," never as "stop" — this prevents a flaky Wi-Fi moment from prematurely ending an in-progress session.
- The "one active session system-wide" invariant (mirrored on the server in three places — see §6) is implicit in the firmware too: it only ever tracks a single `currentSession`.

---

## 6. Notable Issues / Things to Review

1. **Schema drift (init script is behind the live DB).** `init_db.py` + `db_adjust_teachers.sql` together do *not* reproduce the shipped `attendance.db`: they're missing the `ArchivedOfferings` table and the `credit` column on `Courses`. A fresh deployment built only from these two scripts would break the dashboard's archive queries and any code reading `Courses.credit`. A consolidated/updated migration is recommended.
2. **Weak student authentication.** Students log in with `student_id` + their own full `name` as the password — this is public/guessable information, not a real credential.
3. **Hardcoded secrets in firmware.** `rfid_esp32.ino` hardcodes the Wi-Fi SSID/password, the live Render server URL, and the `DEVICE_API_KEY` (still left at the `"dev-only-change-me"` default) directly in source. Anyone with the `.ino` file has the production API key.
4. **TLS certificate verification disabled.** All device HTTP calls use `WiFiClientSecure::setInsecure()`, so the device does not verify the server's TLS certificate (vulnerable to MITM on the local network).
5. **Duplicated single-session invariant.** "Only one session can be Open at a time" is enforced independently in `api/sessions.py`, `ui.py`'s `start_session_remote`, and implicitly relied upon by `api/device.py` and the firmware. Any future move to multiple physical readers would need to revisit all of these together.
6. **Plaintext teacher passwords.** `Teachers.password` is stored and compared as plaintext in `ui.py`'s login route — no hashing.

---

## 7. Deployment

- **Backend**: deployed on Render (per the `Procfile` and the URL hardcoded in the firmware: `https://rfid-attendance-system-c42q.onrender.com`), served via `gunicorn app:app`.
- **Firmware**: flashed to the ESP32 via the Arduino IDE; requires the `Adafruit_GFX`, `Adafruit_SSD1306`, `Adafruit_PN532`, `ArduinoJson`, and standard `WiFi`/`HTTPClient` ESP32 libraries.

