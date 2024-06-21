import requests
from bs4 import BeautifulSoup
import logging
import os
import json
from urllib.parse import urljoin  # Importar urljoin para manipular URLs
from config import API_TOKEN, CHAT_ID

# Configurar el logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if not API_TOKEN:
    raise ValueError("API_TOKEN is not set. Please ensure it's available in the environment variables.")
if not CHAT_ID:
    raise ValueError("CHAT_ID is not set. Please ensure it's available in the environment variables.")

URL_BASE = "https://foros.3dgames.com.ar/"
URL = 'https://foros.3dgames.com.ar/threads/942062-ofertas-online-argentina/page550000000'
POST_CONTAINER_CLASS = 'postcontainer'
POST_ROW_CLASS = 'postrow'
POST_ROW_CLASS_CONTENT = 'content'
NODE_CONTROLS_CLASS = 'nodecontrols'
BBCODE_CONTAINER_CLASS = 'bbcode_container'
NODE_CONTROLS_LINK_CLASS = 'postcounter'
LAST_ID_FILE = 'last_id.txt'
BODY_ID_FILE = 'body_and_id.txt'
TELEGRAM_API_URL = f'https://api.telegram.org/bot{API_TOKEN}/sendMessage'

def get_last_id():
    try:
        with open(LAST_ID_FILE, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

def save_last_id(id):
    with open(LAST_ID_FILE, 'w') as file:
        file.write(id)

def send_telegram_message(chat_id, text, parse_mode='HTML'):
    try:
        response = requests.post(TELEGRAM_API_URL, data={'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode})
        response.raise_for_status()
        logging.info('Mensaje enviado a Telegram')
    except requests.exceptions.RequestException as e:
        logging.error(f'Error al enviar mensaje a Telegram: {e}')

def save_body_and_id(body, id, hrefs, reply_to):
    message = "<b>ID: " + id + "</b>\n\n"
    if reply_to:
        message += "<code>" + reply_to + "</code>\n\n\n"
    if body:
        message += body + "\n\n"
    if hrefs:
        message += "Links:\n" + "\n\n".join(hrefs)
    send_telegram_message(CHAT_ID, message)

def download_images(urls):
    logging.info(f"Fotos a descargar {urls}")
    photos = []
    for url in urls:
        response = requests.get(url)
        logging.info(f"Fotos a descargar {response}")
        if response.status_code == 200:
            logging.info("Foto descargada")
            photos.append(response.content)
    return photos

def send_media_group(media_list, caption):
    try:
        url = f'https://api.telegram.org/bot{API_TOKEN}/sendMediaGroup'
        files = {}
        payload = []
        
        for i, media in enumerate(media_list):
            file_id = f'photo{i}'
            file_content = media if isinstance(media, bytes) else requests.get(media).content
            files[file_id] = ('image.jpg', file_content)
            payload.append({
                'type': 'photo',
                'caption': f'ID: {caption} - Imagen {i + 1} de {len(media_list)}',
                'media': f'attach://{file_id}'
            })

        requests.post(url, files=files, data={'chat_id': CHAT_ID, 'media': json.dumps(payload)})
        logging.info(f'Imagenes enviado a Telegram')
    except requests.exceptions.RequestException as e:
        logging.error(f'Error al enviar imagen a Telegram: {e}')

def fetch_data():
    try:
        response = requests.get(URL)
        response.raise_for_status()
        logging.info('Solicitud realizada exitosamente a la URL!')

        soup = BeautifulSoup(response.text, 'html.parser')
        post_containers = soup.find_all(class_=POST_CONTAINER_CLASS)

        for container in post_containers:
            post_row = container.find(class_=POST_ROW_CLASS)
            post_row_content = post_row.find(class_=POST_ROW_CLASS_CONTENT)
            node_controls = container.find(class_=NODE_CONTROLS_CLASS)

            if post_row_content and node_controls:
                bbcode_containers = post_row_content.find_all(class_=BBCODE_CONTAINER_CLASS)
                body_reply_to = "\n\n".join(bbcode.get_text('\n',strip=True) for bbcode in bbcode_containers)

                # Eliminar bbcode_container
                for bbcode in post_row_content.find_all(class_=BBCODE_CONTAINER_CLASS):
                    bbcode.decompose()

                links = post_row_content.find_all('a')
                hrefs = [link.get('href') for link in links]

                images = post_row_content.find_all('img')
                images_to_send = [image.get('src') for image in images if 'imgur' not in image.get('src', '')]
                logging.info(f'IMAGES {images_to_send}')

                # Obtener todos los hrefs dentro de node_controls
                node_links = node_controls.find_all(class_=NODE_CONTROLS_LINK_CLASS)
                hrefs.extend(urljoin(URL_BASE, link.get('href')) for link in node_links)

                # Eliminar todos los tags <a>
                for a_tag in post_row_content.find_all('a'):
                    a_tag.decompose()

                body = post_row_content.get_text('\n',strip=True)
                body_id = node_controls.get_text(strip=True).replace("#", "")

                if body_id:  # Check if 'id' is not None
                    last_id = get_last_id()
                    logging.info(f'body_id: {body_id}')

                    if last_id is not None and body_id > last_id:
                        if len(images_to_send) > 0:
                            image_data_list = download_images(images_to_send)
                            send_media_group(image_data_list, body_id)
                        save_body_and_id(body, body_id, hrefs, body_reply_to)
                        save_last_id(body_id)
                        logging.info(f'Nuevo ID encontrado y guardado: {body_id}')

    except requests.exceptions.RequestException as e:
        logging.error(f'Ocurrió un error al realizar la solicitud: {e}')

def job():
    fetch_data()

# Ejecutar inmediatamente
fetch_data()