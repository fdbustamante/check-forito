// Worker de Cloudflare que hace de proxy de lectura para foros.3dgames.com.ar.
// Cloudflare bloquea las IPs de GitHub Actions, pero las peticiones que salen
// desde el edge de Cloudflare si pueden acceder al foro.
//
// Deploy:
//   1. Workers & Pages -> Create -> Worker -> pegar este codigo -> Deploy.
//   2. Settings -> Variables -> Add secret: PROXY_TOKEN = <token largo y random>.
//   3. Usar la URL https://<worker>.<subdominio>.workers.dev como FORUM_WORKER_URL
//      y el mismo token como FORUM_WORKER_TOKEN en GitHub Actions.

const ALLOWED_APEX = '3dgames.com.ar';
const ALLOWED_SUFFIX = '.3dgames.com.ar';

export default {
  async fetch(request, env) {
    const requestUrl = new URL(request.url);
    const target = requestUrl.searchParams.get('url');
    const token =
      requestUrl.searchParams.get('token') ||
      request.headers.get('x-proxy-token') ||
      '';

    const expectedToken = env && env.PROXY_TOKEN;
    if (expectedToken && token !== expectedToken) {
      return new Response('forbidden', { status: 403 });
    }
    if (!target) {
      return new Response('missing url', { status: 400 });
    }

    let targetUrl;
    try {
      targetUrl = new URL(target);
    } catch {
      return new Response('invalid url', { status: 400 });
    }

    const host = targetUrl.hostname.toLowerCase();
    if (targetUrl.protocol !== 'https:' ||
        (host !== ALLOWED_APEX && !host.endsWith(ALLOWED_SUFFIX))) {
      return new Response('host not allowed', { status: 403 });
    }

    let upstream;
    try {
      upstream = await fetch(targetUrl.toString(), {
        headers: {
          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
          'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
          'accept-language': 'es-AR,es;q=0.9,en;q=0.8',
        },
        redirect: 'follow',
      });
    } catch (e) {
      return new Response('upstream error: ' + e.message, { status: 502 });
    }

    const headers = new Headers();
    headers.set('content-type', upstream.headers.get('content-type') || 'application/octet-stream');
    headers.set('cache-control', 'no-store');
    headers.set('x-proxy-status', String(upstream.status));
    return new Response(upstream.body, { status: upstream.status, headers });
  },
};
