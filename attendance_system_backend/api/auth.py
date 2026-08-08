from functools import wraps

from flask import jsonify, request

from config import DEVICE_API_KEY


def require_api_key(view):
    """Protects an /api endpoint with a shared-secret header check.

    The caller (ESP32 device, admin scripts, etc.) must send:
        X-API-Key: <DEVICE_API_KEY>

    This does not replace per-user auth (there is no per-user auth for
    devices) -- it just stops the internet at large from hitting these
    endpoints. Keep DEVICE_API_KEY set via an environment variable in
    production.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        supplied_key = request.headers.get("X-API-Key", "")

        if not DEVICE_API_KEY or supplied_key != DEVICE_API_KEY:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        return view(*args, **kwargs)

    return wrapped