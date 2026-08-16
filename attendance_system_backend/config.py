import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "attendance.db"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")

# Shared secret the ESP32 (and any other API caller) must send in the
# X-API-Key header to reach the /api endpoints. Set a real value via the
# DEVICE_API_KEY environment variable in production -- the fallback below
# is only for local development.
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "dev-only-change-me")

# Gmail SMTP settings for absence-notification emails. Use a Gmail App
# Password (Google Account -> Security -> App Passwords), not the
# regular account password -- Gmail blocks plain-password SMTP logins.
# Never commit real values; set these via environment variables.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Attendance System")