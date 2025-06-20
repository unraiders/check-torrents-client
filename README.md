# CHECK-TORRENTS-CLIENT

Utilidad para comprobar los torrents con estado no-tracker, pausados, con error o arhivos faltantes en los clientes qBittorrent, Transmission y Synology Download Station con notificaciones a Telegram o Discord.

### Configuración variables de entorno en fichero .env (renombrar el env-example a .env)

| VARIABLE                | NECESARIA | VERSIÓN | VALOR |
|:----------------------- |:---------:| :------:| :-------------|
| TORRENT_CLIENT          |     ✅    | v1.1.0  | Cliente de descarga de Torrents. (qbittorrent, transmission o synology_ds) |
| TORRENT_CLIENT_HOST     |     ✅    | v1.0.0  | Host/IP del cliente Torrent. Ejemplo: 192.168.2.20  |
| TORRENT_CLIENT_PORT     |     ✅    | v1.0.0  | Puerto del cliente Torrent. Ejemplo: 8090 |
| TORRENT_CLIENT_USER     |     ✅    | v1.0.0  | Usuario del cliente Torrent. |
| TORRENT_CLIENT_PASSWORD |     ✅    | v1.0.0  | Contraseña del cliente Torrent. |
| CLIENTE_NOTIFICACION    |     ✅    | v2.0.0  | Cliente de notificaciones. (telegram o discord) |
| TELEGRAM_BOT_TOKEN      |     ❌    | v1.0.0  | Telegram Bot Token. |
| TELEGRAM_CHAT_ID        |     ❌    | v1.0.0  | Telegram Chat ID. |
| DISCORD_WEBHOOK         |     ❌    | v2.0.0  | Discord Webhook. |
| PAUSADO                 |     ✅    | v1.0.0  | Umbral de torrents con el estado en pausa para enviar la notificación a Telegram o Discord. |
| NO_TRACKER              |     ✅    | v1.0.0  | Umbral de torrents con el estado tracker "Not working" para enviar la notificación a Telegram o Discord. |
| MISSING_FILES           |     ✅    | v2.2.0  | Umbral de torrents con archivos faltantes para enviar la notificación a Telegram o Discord. |
| NOMBRE                  |     ✅    | v1.0.0  | Incluir nombre/s de torrent/s afectados en la notificación a Telegram o Discord. (0 = No / 1 = Si) |
| RESUMEN                 |     ✅    | v1.0.0  | Incluye un resumen con el estado de todos los torrents en la notificación a Telegram o Discord. (0 = No / 1 = Si) |
| RESUMEN_TRACKERS        |     ✅    | v1.2.0  | Incluye un resumen con la cantidad de torrents en cada tracker en la notificación a Telegram o Discord. (0 = No / 1 = Si). |
| INSTANCIA               |     ❌    | v2.1.0  | Incluye en la notificación a Telegram o Discord el nombre de la instancia, detalles https://github.com/unraiders/check-torrents-client/releases/tag/v2.1.0 |
| CRON                    |     ✅    | v1.0.0  | Hora / fecha de ejecución. (formato crontab). ej., 0 7 * * * = cada día a las 7:00 AM, visita https://crontab.guru/ para más info. |
| DEBUG                   |     ✅    | v1.0.0  | Habilita el modo Debug en el log. (0 = No / 1 = Si) |
| TZ                      |     ✅    | v1.0.1  | Timezone (Por ejemplo: Europe/Madrid) |

La VERSIÓN indica cuando se añadió esa variable o cuando sufrió alguna actualización. Consultar https://github.com/unraiders/check-torrents-client/releases

---

Te puedes descargar la imagen del icono desde aquí: https://raw.githubusercontent.com/unraiders/check-torrents-client/master/check-torrents-client-icon.png

---

### Ejemplo docker-compose.yml (con fichero .env aparte)
```yaml
services:
  check-torrents-client:
    image: unraiders/check-torrents-client
    container_name: check-torrents-client
    restart: unless-stopped
    env_file:
      - .env
```

---

### Ejemplo docker-compose.yml (con variables incorporadas)
```yaml
services:
  check-torrents-client:
    image: unraiders/check-torrents-client
    container_name: check-torrents-client
    restart: unless-stopped
    environment:
        - TORRENT_CLIENT=
        - TORRENT_CLIENT_HOST=
        - TORRENT_CLIENT_PORT=
        - TORRENT_CLIENT_USER=
        - TORRENT_CLIENT_PASSWORD=
        - CLIENTE_NOTIFICACION=
        - TELEGRAM_BOT_TOKEN=
        - TELEGRAM_CHAT_ID=
        - DISCORD_WEBHOOK=
        - PAUSADO=1
        - NO_TRACKER=1
        - MISSING_FILES=1
        - NOMBRE=1
        - RESUMEN=1
        - RESUMEN_TRACKERS=1
        - INSTANCIA=
        - CRON=0 7 * * *
        - DEBUG=0
        - TZ=Europe/Madrid
```

---

## Instalación plantilla en Unraid.

- Nos vamos a una ventana de terminal en nuestro Unraid, pegamos esta línea y enter:
```sh
wget -O /boot/config/plugins/dockerMan/templates-user/my-check-torrents-client.xml https://raw.githubusercontent.com/unraiders/check-torrents-client/refs/heads/main/my-check-torrents-client.xml
```
- Nos vamos a DOCKER y abajo a la izquierda tenemos el botón "AGREGAR CONTENEDOR" hacemos click y en seleccionar plantilla seleccionamos check-torrents-client y rellenamos las variables de entorno necesarias, tienes una explicación en cada variable en la propia plantilla.

---

  > [!IMPORTANT]
  > Si seleccionas Discord como destino de tus notificaciones tienes que crear un webhook en el canal que tengas dentro de tu
  > servidor de Discord, nos vamos dentro de nuestro servidor al canal elegido y le damos a la rueda para editar el canal, una vez 
  > dentro nos vamos a Integraciones -> Webhooks y botón "Nuevo webhook", entramos dentro de el, podemos editar el nombre y el 
  > canal donde publicará ese webhook, ya está, le damos al botón "Copiar URL de webhook" y esa URL la pegamos en la variable 
  > DISCORD_WEBHOOK.

---

---

  > [!IMPORTANT]
  > Si seleccionamos synology_ds es importante que el usuario NO tenga activado el doble factor de autenticación.

---

  > [!TIP]
  > Funcionando en:
  >  - qBittorrent v4.6.5
  >  - Transmission v4.0.5
  >  - Synology Download Station 4.0.3-4720
  >  - Es posible que funcione en versiones anteriores y posteriores de estos clientes.

---

## Preview 😎

![alt text](https://github.com/unraiders/imagenes/blob/main/check-torrents-client-image.jpeg)

Fin.

