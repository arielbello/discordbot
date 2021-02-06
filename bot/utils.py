import os


def create_folder_if_needed(path):
    if not os.path.exists(path):
        os.makedirs(path)


def format_time(hour: int, minute: int) -> str:
    """Turns hours and minutes to a string with the format 'HH:MM'. Assumes 24h clock"""
    return f"{str(hour).rjust(2, '0')}:{str(minute).rjust(2, '0')}"