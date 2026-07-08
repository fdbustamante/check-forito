import logging

import requests

from formatter import build_message
from scraper import collect_new_posts
from storage import load_state, save_state
from telegram_client import download_image, send_media_group, send_telegram_message

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def publish(post):
    logging.info('Publicando post %s (imgs=%s)', post.post_id, len(post.images))
    if post.images:
        downloaded = [d for d in (download_image(u) for u in post.images) if d]
        if not send_media_group(downloaded, post.post_id):
            return False
    message = build_message(post)
    if message and not send_telegram_message(message):
        return False
    return True


def main():
    state = load_state()
    logging.info('estado inicial: %s', state)

    try:
        posts = collect_new_posts(state)
    except requests.RequestException as e:
        logging.error('Error al obtener el thread: %s', e)
        return

    if not posts:
        logging.info('Sin posts nuevos')
        return

    if state['last_id'] is None:
        latest = max(posts, key=lambda p: p.post_id)
        save_state(latest.post_id, latest.page)
        logging.info('Primera corrida, guardado last_id=%s last_page=%s sin publicar',
                     latest.post_id, latest.page)
        return

    logging.info('Posts nuevos a publicar: %s', len(posts))
    for post in posts:
        if not publish(post):
            logging.warning('Fallo al publicar post %s; continuando con los siguientes', post.post_id)
        else:
            save_state(post.post_id, post.page)
            logging.info('Publicado y guardado ID %s pagina %s', post.post_id, post.page)


if __name__ == '__main__':
    main()
