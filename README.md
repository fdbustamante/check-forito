# check-forito

Bot que lee el thread de ofertas de 3DGames y publica los posts nuevos en Telegram.

## Situacion actual (noviembre 2026)

El foro esta detrás de Cloudflare y **bloquea por IP/ASN las IPs de datacenter**,
incluidos los runners de GitHub Actions. Se probaron:

- `curl_cffi` con huella TLS de Chrome, Safari, Firefox y Edge.
- Headers completos de navegador (`sec-ch-ua`, `sec-fetch-*`, etc.).
- User-Agent móvil, Googlebot y el RSS del thread.
- Un Cloudflare Worker propio (funciona desde algunas ubicaciones, pero no desde
  los runners de EE. UU. de GitHub Actions).
- Tapatalk (`/mobiquo/mobiquo.php`), que está detrás del mismo challenge.

Desde Actions, **todas** las variantes reciben `403 Attention Required!`, que es un
bloqueo duro del WAF (no un challenge que se pueda resolver). Por eso la solución
confiable es salir por una IP residencial.

## Opción recomendada: self-hosted runner

Usa tu PC (IP residencial) para ejecutar el workflow de GitHub Actions. Sigue
siendo GitHub Actions, con el cron y los logs en GitHub, pero la descarga la hace
tu conexión.

1. En GitHub: **Settings -> Actions -> Runners -> New self-hosted runner**.
2. Elegí **Windows x64** y seguí las instrucciones (descargar, `config.cmd`,
   `svc.cmd install` / `svc.cmd start`).
3. En `.github/workflows/python-app.yml`, cambiar:
   - `runs-on: ubuntu-latest` por `runs-on: self-hosted`.
   - Agregar `shell: bash` al step **Commit changes**.
   - Quitar `FORUM_WORKER_URL`, `FORUM_WORKER_TOKEN` y `FORUM_PROXY_URL` del `env`
     (con IP residencial no hacen falta).
4. Asegurate de que la PC no se duerma (Configuración de energía -> Nunca).
5. Ejecutar el workflow con **Run workflow**.

## Opción alternativa: proxy residencial

Si querés seguir en la nube de GitHub sin mantener una PC prendida, configurá el
secret `FORUM_PROXY_URL` con un proxy HTTP/HTTPS residencial
(`http://usuario:clave@host:puerto`). Quitá `FORUM_WORKER_URL` para que el bot
vaya directo a través del proxy. Tiene costo mensual.

## Cloudflare Worker (experimental)

El Worker de [`cloudflare-worker.js`](cloudflare-worker.js) puede leer el foro
desde algunos colos de Cloudflare (por ejemplo, desde Argentina funcionó), pero
desde los runners de GitHub Actions el foro respondió `403 Attention Required!`.
No es una solución estable para Actions; queda como alternativa si el Worker se
ejecuta desde una ubicación permitida.

Para desplegarlo: crear un Worker en el dashboard de Cloudflare, pegar el
contenido de `cloudflare-worker.js`, agregar el secret `PROXY_TOKEN` y configurar
`FORUM_WORKER_URL` + `FORUM_WORKER_TOKEN` en GitHub. El Worker solo permite URLs
de `3dgames.com.ar` y exige el token si `PROXY_TOKEN` está configurado.

## Estado

`state.json` guarda `last_id` y `last_page`. Está en `10209` / `681` (último post
al 9 de noviembre de 2026). `MAX_POSTS_PER_RUN` limita a 10 los posts publicados
por corrida para no inundar Telegram.
