import html
from urllib.parse import urlparse


def _render_links(urls, label=''):
    if not urls:
        return ''
    return '\n'.join(
        f'• {label}<a href="{html.escape(u, quote=True)}">{html.escape(urlparse(u).netloc or u)}</a>'
        for u in urls
    )


def _render_quote(post):
    inner_parts = []
    if post.reply_to:
        inner_parts.append(html.escape(post.reply_to))
    images_block = _render_links(post.reply_images, label='imagen: ')
    if images_block:
        inner_parts.append(images_block)
    return '<blockquote>' + '\n\n'.join(inner_parts) + '</blockquote>'


def build_message(post):
    header = f'<b>Post #{post.post_id}</b>'
    if post.url:
        header += f' — <a href="{html.escape(post.url, quote=True)}">ver en el foro</a>'
    parts = [header]
    if post.reply_to or post.reply_images:
        parts.append(_render_quote(post))
    if post.body:
        parts.append(html.escape(post.body))
    if post.hrefs:
        parts.append('<b>Enlaces:</b>\n' + _render_links(post.hrefs))
    return '\n\n'.join(parts)
