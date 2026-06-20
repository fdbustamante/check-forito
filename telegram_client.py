import json
import logging

import requests

from config import API_TOKEN, CHAT_ID
from constants import REQUEST_TIMEOUT, TELEGRAM_API, TELEGRAM_MESSAGE_LIMIT

session = requests.Session()


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


def send_media_group(images, post_id):
    if not images:
        return True
    url = f'{TELEGRAM_API}/bot{API_TOKEN}/sendMediaGroup'
    files = {}
    payload = []
    for i, content in enumerate(images):
        file_id = f'photo{i}'
        files[file_id] = ('image.jpg', content)
        payload.append({
            'type': 'photo',
            'caption': f'Post #{post_id} — imagen {i + 1}/{len(images)}',
            'media': f'attach://{file_id}',
        })
    try:
        response = session.post(url, files=files, data={
            'chat_id': CHAT_ID,
            'media': json.dumps(payload),
        }, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logging.info('Imagenes enviadas a Telegram')
        return True
    except requests.RequestException as e:
        logging.error('Error al enviar imagenes a Telegram: %s', e)
        return False
