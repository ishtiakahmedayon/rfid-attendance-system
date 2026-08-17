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

#
# RESEND_FROM_EMAIL must be either:
#   - the Resend sandbox address "onboarding@resend.dev" (no setup,
#     but Resend will only actually deliver those to your OWN Resend
#     account email -- fine for testing, not for real students), or
#   - an address on a domain you've verified in the Resend dashboard
#     (e.g. "attendance@yourdomain.com") -- required for production,
#     since no email provider can send *as* an address on a domain
#     (like gmail.com) you don't control.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
RESEND_FROM_NAME = os.getenv("RESEND_FROM_NAME", "Attendance System")