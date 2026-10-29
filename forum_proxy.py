import os
from urllib.parse import quote

# URL base del Cloudflare Worker que hace de proxy (ej: https://forito.xxx.workers.dev).
FORUM_WORKER_URL = (os.environ.get('FORUM_WORKER_URL') or '').rstrip('/')
FORUM_WORKER_TOKEN = os.environ.get('FORUM_WORKER_TOKEN') or ''


def worker_url(target):
    """Devuelve la URL del Worker para un target, o None si no hay Worker configurado."""
    if not FORUM_WORKER_URL:
        return None
    url = f'{FORUM_WORKER_URL}/?url={quote(target, safe="")}'
    if FORUM_WORKER_TOKEN:
        url += f'&token={quote(FORUM_WORKER_TOKEN, safe="")}'
    return url
