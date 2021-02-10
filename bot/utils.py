import os
from datetime import datetime, timedelta


def create_folder_if_needed(path):
    if not os.path.exists(path):
        os.makedirs(path)


def format_time(hour: int, minute: int) -> str:
    """Turns hours and minutes to a string with the format 'HH:MM'. Assumes 24h clock"""
    return f"{str(hour).rjust(2, '0')}:{str(minute).rjust(2, '0')}"


def time_now_with_tz(tz):
    """Timezone aware clock"""
    assert tz is not None
    now = datetime.utcnow() + timedelta(hours=tz)
    return format_time(now.hour, now.minute)


def offset_format(utc_offset):
    """Display + or - in front of UTC offset number"""
    return str(utc_offset) if utc_offset < 0 else f"+{str(utc_offset)}"
