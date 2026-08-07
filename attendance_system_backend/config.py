import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "attendance.db"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
