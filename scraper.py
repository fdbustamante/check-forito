import logging
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from constants import (
    BBCODE_CONTAINER_CLASS,
    LAST_PAGE_PROBE,
    NODE_CONTROLS_CLASS,
    NODE_CONTROLS_LINK_CLASS,
    PAGINATION_SELECTED_CLASS,
    PAGINATION_TOP_ID,
    POST_CONTAINER_CLASS,
    POST_ROW_CLASS,
    POST_ROW_CLASS_CONTENT,
    REQUEST_TIMEOUT,
    THREAD_URL,
    URL_BASE,
)
from models import Post

PAGE_RE = re.compile(r'/page(\d+)')

session = requests.Session()


def page_url(n):
    return f'{THREAD_URL}/page{n}'


def fetch_page(url):
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response


def extract_page_number(url):
    match = PAGE_RE.search(url)
    return int(match.group(1)) if match else 1


def extract_current_page(soup, fallback_url):
    pagination = soup.find(id=PAGINATION_TOP_ID)
    if pagination:
        selected = pagination.find(class_=PAGINATION_SELECTED_CLASS)
        if selected:
            text = selected.get_text(strip=True)
            if text.isdigit():
                return int(text)
    return extract_page_number(fallback_url)


def _extract_hrefs(node):
    seen = set()
    hrefs = []
    for a in node.find_all('a'):
        href = a.get('href')
        if not href:
            continue
        absolute = urljoin(URL_BASE, href)
        if absolute not in seen:
            seen.add(absolute)
            hrefs.append(absolute)
    return hrefs


def _extract_images(node):
    return [urljoin(URL_BASE, img.get('src'))
            for img in node.find_all('img')
            if img.get('src') and not img.get('src', '').endswith('.gif')]


def _parse_container(container):
    post_row = container.find(class_=POST_ROW_CLASS)
    if not post_row:
        return None
    content = post_row.find(class_=POST_ROW_CLASS_CONTENT)
    node_controls = container.find(class_=NODE_CONTROLS_CLASS)
    if not (content and node_controls):
        return None

    raw_id = re.sub(r'\D', '', node_controls.get_text(strip=True))
    if not raw_id:
        return None
    post_id = int(raw_id)

    post_link = node_controls.find('a', class_=NODE_CONTROLS_LINK_CLASS)
    post_url = urljoin(URL_BASE, post_link.get('href')) if post_link and post_link.get('href') else ''

    bbcodes = content.find_all(class_=BBCODE_CONTAINER_CLASS)
    reply_to = "\n\n".join(b.get_text('\n', strip=True) for b in bbcodes)
    reply_hrefs = []
    reply_images = []
    for b in bbcodes:
        reply_hrefs.extend(_extract_hrefs(b))
        reply_images.extend(_extract_images(b))
    reply_hrefs = list(dict.fromkeys(reply_hrefs))
    reply_images = list(dict.fromkeys(reply_images))
    for b in bbcodes:
        b.decompose()

    hrefs = _extract_hrefs(content)
    images = _extract_images(content)

    for a in content.find_all('a'):
        a.decompose()

    body = content.get_text('\n', strip=True)

    return Post(post_id=post_id, body=body, reply_to=reply_to,
                url=post_url, hrefs=hrefs, images=images,
                reply_hrefs=reply_hrefs, reply_images=reply_images)


def parse_posts(soup):
    posts = []
    for container in soup.find_all(class_=POST_CONTAINER_CLASS):
        post = _parse_container(container)
        if post is not None:
            posts.append(post)
    return posts


def collect_new_posts(last_id):
    response = fetch_page(page_url(LAST_PAGE_PROBE))
    soup = BeautifulSoup(response.text, 'html.parser')
    current_page = extract_current_page(soup, response.url)
    logging.info('Ultima pagina detectada: %s', current_page)

    collected = []
    while True:
        posts = parse_posts(soup)
        logging.info('Pagina %s, posts=%s', current_page, len(posts))
        if not posts:
            break

        if last_id is None:
            collected.extend(posts)
            break

        collected.extend(p for p in posts if p.post_id > last_id)

        min_id = min(p.post_id for p in posts)
        if min_id <= last_id or current_page <= 1:
            break

        current_page -= 1
        response = fetch_page(page_url(current_page))
        soup = BeautifulSoup(response.text, 'html.parser')

    collected.sort(key=lambda p: p.post_id)
    return collected
