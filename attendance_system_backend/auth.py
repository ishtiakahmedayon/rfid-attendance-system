from functools import wraps

from flask import jsonify, request

from config import DEVICE_API_KEY


def require_api_key(view):
    """Protects device-facing endpoints (ESP32 scanner) with a shared
    secret sent as the X-API-Key header. Does not affect the browser
    session-based login used by ui.py."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        if not key or key != DEVICE_API_KEY:
            return jsonify({"success": False, "error": "Invalid or missing API key"}), 401
        return view(*args, **kwargs)

    return wrapped
