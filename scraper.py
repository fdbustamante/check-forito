import logging
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from constants import (
    BBCODE_CONTAINER_CLASS,
    BBCODE_QUOTE_MESSAGE_CLASS,
    LAST_PAGE_PROBE,
    NODE_CONTROLS_CLASS,
    NODE_CONTROLS_LINK_CLASS,
    PAGINATION_NEXT_REL,
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
    quote_msgs = [b.find(class_=BBCODE_QUOTE_MESSAGE_CLASS) or b for b in bbcodes]
    for m in quote_msgs:
        for a in m.find_all('a'):
            if a.get('href'):
                a.string = a['href']
    reply_to = "\n\n".join(m.get_text('\n', strip=True) for m in quote_msgs)
    reply_images = []
    for m in quote_msgs:
        reply_images.extend(_extract_images(m))
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
                reply_images=reply_images)


def parse_posts(soup):
    posts = []
    for container in soup.find_all(class_=POST_CONTAINER_CLASS):
        post = _parse_container(container)
        if post is not None:
            posts.append(post)
    return posts


def has_next_page(soup, current_page):
    pagination = soup.find(id=PAGINATION_TOP_ID)
    if not pagination:
        return False
    if pagination.find('a', attrs={'rel': PAGINATION_NEXT_REL}):
        return True
    for a in pagination.find_all('a'):
        match = PAGE_RE.search(a.get('href', ''))
        if match and int(match.group(1)) > current_page:
            return True
    return False


def _load_page(url):
    response = fetch_page(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    current_page = extract_current_page(soup, response.url)
    posts = parse_posts(soup)
    for p in posts:
        p.page = current_page
    return soup, current_page, posts


def collect_new_posts(state):
    last_id = state.get('last_id')
    last_page = state.get('last_page')

    start_url = page_url(last_page) if last_page else page_url(LAST_PAGE_PROBE)
    soup, current_page, posts = _load_page(start_url)
    logging.info('Pagina inicial %s, posts=%s', current_page, len(posts))

    if last_id is None:
        return posts

    collected = [p for p in posts if p.post_id > last_id]
    while has_next_page(soup, current_page):
        soup, current_page, posts = _load_page(page_url(current_page + 1))
        logging.info('Pagina %s, posts=%s', current_page, len(posts))
        collected.extend(p for p in posts if p.post_id > last_id)

    collected.sort(key=lambda p: p.post_id)
    return collected
