import json
import logging

import requests

from config import API_TOKEN, CHAT_ID
from constants import REQUEST_TIMEOUT, TELEGRAM_API, TELEGRAM_MESSAGE_LIMIT

session = requests.Session()

_IMAGE_SIGNATURES = [
    (b'\x89PNG\r\n\x1a\n', 'image/png', 'png'),
    (b'GIF87a', 'image/gif', 'gif'),
    (b'GIF89a', 'image/gif', 'gif'),
    (b'RIFF', 'image/webp', 'webp'),
    (b'\xff\xd8\xff', 'image/jpeg', 'jpg'),
]


def _detect_image_type(content):
    for sig, mime, ext in _IMAGE_SIGNATURES:
        if content[:len(sig)].startswith(sig[:4] if ext == 'webp' else sig):
            if ext == 'webp' and len(content) > 8 and content[8:12] != b'WEBP':
                continue
            return mime, ext
    return 'image/jpeg', 'jpg'


def chunk_text(text, limit=TELEGRAM_MESSAGE_LIMIT):
    for i in range(0, len(text), limit):
        yield text[i:i + limit]


def _response_body(e):
    if hasattr(e, 'response') and e.response is not None:
        return e.response.text
    return ''


def _is_rate_limited(e):
    return hasattr(e, 'response') and e.response is not None and e.response.status_code == 429


def _post(url, **kwargs):
    response = session.post(url, timeout=REQUEST_TIMEOUT, **kwargs)
    response.raise_for_status()
    return response


def send_telegram_message(text, parse_mode='HTML'):
    url = f'{TELEGRAM_API}/bot{API_TOKEN}/sendMessage'
    for chunk in chunk_text(text):
        try:
            _post(url, data={
                'chat_id': CHAT_ID,
                'text': chunk,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True,
            })
            logging.info('Mensaje enviado a Telegram')
        except requests.RequestException as e:
            logging.error('Error al enviar mensaje a Telegram: %s', e)
            return False
    return True


def download_image(url):
    headers = {'user-agent': 'curl/8.1.1', 'accept': '*/*'} if 'imgur' in url else {}
    try:
        response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            content = response.content
            if len(content) < 50000:  # ponytail: reject suspiciously small images (thumbnails, corrupted)
                logging.warning('Imagen descartada (too small %sB): %s', len(content), url)
                return None
            return content
        logging.warning('Imagen no descargada (%s): %s', response.status_code, url)
    except requests.RequestException as e:
        logging.error('Error descargando imagen %s: %s', url, e)
    return None




def _send_with_retry(images, post_id):
    url = f'{TELEGRAM_API}/bot{API_TOKEN}/sendMediaGroup'
    files = {}
    payload = []
    for i, content in enumerate(images):
        file_id = f'photo{i}'
        mime, ext = _detect_image_type(content)
        files[file_id] = (f'image.{ext}', content, mime)
        entry = {'type': 'photo', 'media': f'attach://{file_id}'}
        if i == 0:
            entry['caption'] = f'Post #{post_id}'
        payload.append(entry)
    _post(url, files=files, data={
        'chat_id': CHAT_ID,
        'media': json.dumps(payload),
    })


def send_media_group(images, post_id):
    if not images:
        return True
    try:
        _send_with_retry(images, post_id)
        logging.info('Imagenes enviadas a Telegram')
        return True
    except requests.RequestException as e:
        logging.warning('sendMediaGroup fallo (%s), reintentando imagen por imagen. %s', e, _response_body(e))

    # Retry one by one to skip unprocessable images (IMAGE_PROCESS_FAILED)
    good = []
    for i, content in enumerate(images):
        try:
            _send_with_retry([content], post_id)
            good.append(content)
        except requests.RequestException as e:
            if _is_rate_limited(e):
                logging.error('Rate limit al enviar imagenes para post %s: %s', post_id, _response_body(e))
                return False
            logging.warning('Imagen %s/%s descartada (IMAGE_PROCESS_FAILED): %s', i + 1, len(images), _response_body(e))

    if not good:
        logging.error('Ninguna imagen pudo enviarse para post %s', post_id)
        return False

    if len(good) < len(images):
        # Re-send all good ones together (already sent individually above, but we want them grouped)
        try:
            _send_with_retry(good, post_id)
        except requests.RequestException as e:
            logging.error('Error al reagrupar imagenes: %s', e)

    logging.info('%s/%s imagenes enviadas para post %s', len(good), len(images), post_id)
    return True
