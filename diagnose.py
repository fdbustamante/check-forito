"""Diagnostico temporal: prueba variantes contra el foro desde el runner."""
import json
import re

from curl_cffi import requests

URL = 'https://foros.3dgames.com.ar/threads/1111950-ofertas-online-argentina-2-0/page607'
RSS = 'https://foros.3dgames.com.ar/threads/1111950/index.rss'

CHROME_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
             '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
CHROME_FULL = {
    'User-Agent': CHROME_UA,
    'Accept': ('text/html,application/xhtml+xml,application/xml;q=0.9,'
               'image/avif,image/webp,image/apng,*/*;q=0.8,'
               'application/signed-exchange;v=b3;q=0.7'),
    'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
    'Sec-CH-UA': '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    'Sec-CH-UA-Mobile': '?0',
    'Sec-CH-UA-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}
MOBILE = {
    'User-Agent': ('Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
}

VARIANTS = [
    ('chrome-impersonate', URL, {'impersonate': 'chrome'}),
    ('chrome-full-headers', URL, {'impersonate': 'chrome', 'headers': CHROME_FULL}),
    ('safari-impersonate', URL, {'impersonate': 'safari'}),
    ('firefox-impersonate', URL, {'impersonate': 'firefox'}),
    ('edge-impersonate', URL, {'impersonate': 'edge101'}),
    ('mobile-chrome', URL, {'impersonate': 'chrome', 'headers': MOBILE}),
    ('googlebot', URL, {'headers': {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}}),
    ('rss-chrome', RSS, {'impersonate': 'chrome'}),
    ('rss-full-headers', RSS, {'impersonate': 'chrome', 'headers': CHROME_FULL}),
    ('www-host', 'https://www.3dgames.com.ar/threads/1111950-ofertas-online-argentina-2-0/page607', {'impersonate': 'chrome'}),
]


def title_of(text):
    m = re.search(r'<title>(.*?)</title>', text, re.S | re.I)
    return ' '.join(m.group(1).split())[:80] if m else ''


for name, url, kwargs in VARIANTS:
    try:
        r = requests.get(url, timeout=30, **kwargs)
        line = {
            'name': name,
            'status': r.status_code,
            'len': len(r.text),
            'title': title_of(r.text),
            'cf': r.headers.get('cf-mitigated'),
            'server': r.headers.get('server'),
        }
    except Exception as e:
        line = {'name': name, 'error': type(e).__name__ + ': ' + str(e)[:80]}
    print('::error::DIAG ' + json.dumps(line, ensure_ascii=False), flush=True)

print('::error::DIAG done', flush=True)
