import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin  # Importar urljoin para manipular URLs

# Configurar el logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

URL_BASE = "https://foros.3dgames.com.ar/"
URL = 'https://foros.3dgames.com.ar/threads/942062-ofertas-online-argentina/page544200000'
POST_CONTAINER_CLASS = 'postcontainer'
POST_ROW_CLASS = 'postrow'
NODE_CONTROLS_CLASS = 'nodecontrols'
BBCODE_CONTAINER_CLASS = 'bbcode_container'
NODE_CONTROLS_LINK_CLASS = 'postcounter'
LAST_ID_FILE = 'last_id.txt'
BODY_ID_FILE = 'body_and_id.txt'
TELEGRAM_API_URL = 'https://api.telegram.org/bot7269598452:AAGMURWCaSd5nhDzFhEKPKl4wlY70dFEbEw/sendMessage'
CHAT_ID = '387808312'

def get_last_id():
    try:
        with open(LAST_ID_FILE, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

def save_last_id(id):
    with open(LAST_ID_FILE, 'w') as file:
        file.write(id)

def send_telegram_message(chat_id, text):
    try:
        response = requests.post(TELEGRAM_API_URL, data={'chat_id': chat_id, 'text': text})
        response.raise_for_status()
        logging.info('Mensaje enviado a Telegram')
    except requests.exceptions.RequestException as e:
        logging.error(f'Error al enviar mensaje a Telegram: {e}')

def save_body_and_id(body, id, hrefs):
    message = "ID: " + id + "\n\n" + body + "\n\n"
    if hrefs:
        message += "Links:\n" + "\n\n".join(hrefs)
    # with open(BODY_ID_FILE, 'a') as file:
    #    file.write(message)
    send_telegram_message(CHAT_ID, message)

def fetch_data():
    try:
        response = requests.get(URL)
        response.raise_for_status()
        logging.info('Solicitud realizada exitosamente a la URL.')

        soup = BeautifulSoup(response.text, 'html.parser')
        post_containers = soup.find_all(class_=POST_CONTAINER_CLASS)

        for container in post_containers:
            post_row = container.find(class_=POST_ROW_CLASS)
            node_controls = container.find(class_=NODE_CONTROLS_CLASS)

            if post_row and node_controls:
                # Eliminar bbcode_container
                for bbcode in post_row.find_all(class_=BBCODE_CONTAINER_CLASS):
                    bbcode.decompose()

                links = post_row.find_all('a')
                hrefs = [link.get('href') for link in links]

                # Obtener todos los hrefs dentro de node_controls
                node_links = node_controls.find_all(class_=NODE_CONTROLS_LINK_CLASS)
                hrefs.extend(urljoin(URL_BASE, link.get('href')) for link in node_links)

                # Eliminar todos los tags <a>
                for a_tag in post_row.find_all('a'):
                    a_tag.decompose()

                body = post_row.get_text('\n',strip=True)
                body_id = node_controls.get_text(strip=True).replace("#", "")

                if body_id:  # Check if 'id' is not None
                    last_id = get_last_id()

                    if last_id is not None and body_id > last_id:
                        logging.info(f"Entro con el {body_id}")
                        save_body_and_id(body, body_id, hrefs)
                        save_last_id(body_id)
                        logging.info(f'Nuevo ID encontrado y guardado: {body_id}')

    except requests.exceptions.RequestException as e:
        logging.error(f'Ocurrió un error al realizar la solicitud: {e}')

def job():
    fetch_data()

# Ejecutar inmediatamente
fetch_data()