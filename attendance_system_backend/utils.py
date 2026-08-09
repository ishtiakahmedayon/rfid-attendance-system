from datetime import datetime, timedelta, timezone

# Bangladesh Standard Time is a fixed UTC+6 offset (no DST), so a fixed
# timezone offset is used instead of relying on the host server's local
# timezone (which may be set to something else, e.g. Singapore/UTC+8).
BD_TZ = timezone(timedelta(hours=6))


def bd_now():
    """Current datetime in GMT+6 (Asia/Dhaka), regardless of server timezone."""
    return datetime.now(BD_TZ)


def bd_today_str():
    return bd_now().strftime("%Y-%m-%d")


def bd_time_str():
    return bd_now().strftime("%H:%M:%S")
