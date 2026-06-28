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


def send_telegram_message(text, parse_mode='HTML'):
    url = f'{TELEGRAM_API}/bot{API_TOKEN}/sendMessage'
    for chunk in chunk_text(text):
        try:
            response = session.post(url, data={
                'chat_id': CHAT_ID,
                'text': chunk,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True,
            }, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
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
            return response.content
        logging.warning('Imagen no descargada (%s): %s', response.status_code, url)
    except requests.RequestException as e:
        logging.error('Error descargando imagen %s: %s', url, e)
    return None


def _send_media_group_request(images, post_id):
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
    response = session.post(url, files=files, data={
        'chat_id': CHAT_ID,
        'media': json.dumps(payload),
    }, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()


def send_media_group(images, post_id):
    if not images:
        return True
    try:
        _send_media_group_request(images, post_id)
        logging.info('Imagenes enviadas a Telegram')
        return True
    except requests.RequestException as e:
        body = e.response.text if hasattr(e, 'response') and e.response is not None else ''
        logging.warning('sendMediaGroup fallo (%s), reintentando sin imagenes problematicas. %s', e, body)

    # Retry sending images one by one, skipping those that fail
    good = []
    for i, content in enumerate(images):
        try:
            _send_media_group_request([content], post_id)
            good.append(content)
        except requests.RequestException as e:
            body = e.response.text if hasattr(e, 'response') and e.response is not None else ''
            logging.warning('Imagen %s/%s descartada (no procesable por Telegram): %s', i + 1, len(images), body)

    if not good:
        logging.error('Ninguna imagen pudo enviarse para post %s', post_id)
        return False

    if len(good) == 1:
        logging.info('1 imagen enviada para post %s', post_id)
        return True

    # Send all good images together
    try:
        _send_media_group_request(good, post_id)
        logging.info('%s imagenes enviadas a Telegram', len(good))
        return True
    except requests.RequestException as e:
        logging.error('Error al enviar imagenes a Telegram: %s', e)
        return False
