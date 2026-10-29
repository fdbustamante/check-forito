# check-forito

Bot que lee el thread de ofertas de 3DGames y publica los posts nuevos en Telegram.

## Por que falla en GitHub Actions

El foro esta detras de Cloudflare y bloquea por ASN las IPs de datacenter
(incluidos los runners de GitHub Actions). `curl_cffi` alcanza desde una IP
residencial, pero no desde Actions. La solucion es salir por una IP que el foro
permita: un Cloudflare Worker propio (gratis) o un proxy residencial.

## Opcion recomendada: Cloudflare Worker

El Worker corre en el edge de Cloudflare y puede leer el foro; el Action le pide
las paginas al Worker.

1. Crear una cuenta gratuita en <https://dash.cloudflare.com/>.
2. Ir a **Workers & Pages -> Create -> Worker**, ponerle un nombre (ej.
   `forito-proxy`) y deployar.
3. **Edit code**, borrar el ejemplo y pegar el contenido de
   [`cloudflare-worker.js`](cloudflare-worker.js). Deploy.
4. En **Settings -> Variables and Secrets**, agregar un **Secret** llamado
   `PROXY_TOKEN` con un valor largo y aleatorio.
5. Copiar la URL publica del Worker, con forma
   `https://forito-proxy.<subdominio>.workers.dev`.
6. En GitHub, ir a **Settings -> Secrets and variables -> Actions** y crear:
   - `FORUM_WORKER_URL`: la URL del Worker.
   - `FORUM_WORKER_TOKEN`: el mismo valor de `PROXY_TOKEN`.
7. Ejecutar el workflow (`Actions -> Run workflow`).

El Worker solo permite pedir URLs de `3dgames.com.ar` y, si `PROXY_TOKEN` esta
configurado, exige el token. No queda como proxy abierto.

### Opcion alternativa: proxy residencial

Configurar el secret `FORUM_PROXY_URL` con un proxy HTTP/HTTPS
(`http://usuario:clave@host:puerto`). El bot lo usa para todas las peticiones al
foro.

### Opcion alternativa: self-hosted runner

Si tenes una PC siempre encendida con IP residencial, podes registrar un
self-hosted runner de GitHub y cambiar `runs-on: ubuntu-latest` por
`runs-on: self-hosted` en `.github/workflows/python-app.yml`. En ese caso no
hace falta Worker ni proxy.
