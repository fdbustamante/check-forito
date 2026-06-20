import logging

import requests

from formatter import build_message
from scraper import collect_new_posts
from storage import get_last_id, save_last_id
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
    last_id = get_last_id()
    logging.info('last_id inicial: %s', last_id)

    try:
        posts = collect_new_posts(last_id)
    except requests.RequestException as e:
        logging.error('Error al obtener el thread: %s', e)
        return

    if not posts:
        logging.info('Sin posts nuevos')
        return

    if last_id is None:
        max_id = max(p.post_id for p in posts)
        save_last_id(max_id)
        logging.info('Primera corrida, guardado last_id=%s sin publicar', max_id)
        return

    logging.info('Posts nuevos a publicar: %s', len(posts))
    for post in posts:
        if not publish(post):
            logging.error('Fallo al publicar post %s; se reintentara en la proxima corrida', post.post_id)
            return
        save_last_id(post.post_id)
        logging.info('Publicado y guardado ID %s', post.post_id)


if __name__ == '__main__':
    main()
