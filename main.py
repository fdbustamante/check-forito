import logging
import os
import sys

from curl_cffi.requests.exceptions import RequestException

from constants import MAX_POSTS_PER_RUN
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
    if os.environ.get('FORUM_WORKER_URL'):
        logging.info('Foro via Cloudflare Worker: %s', os.environ['FORUM_WORKER_URL'])
    elif os.environ.get('FORUM_PROXY_URL'):
        logging.info('Foro via proxy configurado (FORUM_PROXY_URL)')
    else:
        logging.info('Foro sin proxy (IP directa)')

    try:
        posts = collect_new_posts(state)
    except RequestException as e:
        logging.error('Error al obtener el thread: %s', e)
        if os.environ.get('FORUM_WORKER_URL'):
            hint = ('El Worker respondio con error. Verifica FORUM_WORKER_URL y que '
                    'FORUM_WORKER_TOKEN coincida con el secret PROXY_TOKEN del Worker.')
        elif os.environ.get('FORUM_PROXY_URL'):
            hint = 'Verifica que el proxy FORUM_PROXY_URL siga funcionando.'
        else:
            hint = ('Cloudflare bloquea las IPs de GitHub Actions. Configura el secret '
                    'FORUM_WORKER_URL (Cloudflare Worker proxy) o usa un self-hosted runner.')
        print(f'::error::No se pudo leer el foro: {e}. {hint}', flush=True)
        return 1

    if not posts:
        logging.info('Sin posts nuevos')
        return

    if state['last_id'] is None:
        latest = max(posts, key=lambda p: p.post_id)
        save_state(latest.post_id, latest.page)
        logging.info('Primera corrida, guardado last_id=%s last_page=%s sin publicar',
                     latest.post_id, latest.page)
        return

    if len(posts) > MAX_POSTS_PER_RUN:
        logging.warning('Backlog de %s posts; se omiten los mas viejos y se publican los %s recientes',
                        len(posts), MAX_POSTS_PER_RUN)
        posts = posts[-MAX_POSTS_PER_RUN:]

    logging.info('Posts nuevos a publicar: %s', len(posts))
    for post in posts:
        if not publish(post):
            logging.warning('Fallo al publicar post %s; continuando con los siguientes', post.post_id)
        else:
            save_state(post.post_id, post.page)
            logging.info('Publicado y guardado ID %s pagina %s', post.post_id, post.page)


if __name__ == '__main__':
    sys.exit(main())
