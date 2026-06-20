from constants import LAST_ID_FILE


def get_last_id():
    try:
        with open(LAST_ID_FILE, 'r', encoding='utf-8') as f:
            value = f.read().strip()
            return int(value) if value else None
    except (FileNotFoundError, ValueError):
        return None


def save_last_id(post_id):
    with open(LAST_ID_FILE, 'w', encoding='utf-8') as f:
        f.write(str(post_id))
