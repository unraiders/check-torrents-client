# CHECK-TORRENTS-CLIENT

Utilidad para comprobar los torrents con estado no-tracker, pausados o con error en los clientes qBittorrent y Transmission con notificaciones a Telegram.

## Configuración variables de entorno en fichero .env (renombrar el env-example a .env)

| CLAVE  | NECESARIO | VALOR |
|:------------- |:---------------:| :-------------|
|TORRENT_CLIENT |✅| Cliente de descarga de Torrents. (qbittorrent o transmission) |
|TORRENT_CLIENT_HOST |✅| Host/IP del cliente Torrent. Ejemplo: 192.168.2.20  |
|TORRENT_CLIENT_PORT |✅| Puerto del cliente Torrent. Ejemplo: 8090 |
|TORRENT_CLIENT_USER |✅| Usuario del cliente Torrent. |
|TORRENT_CLIENT_PASSWORD |✅| Contraseña del cliente Torrent. |
|TELEGRAM_BOT_TOKEN |✅| Telegram Bot Token. |
|TELEGRAM_CHAT_ID |✅| Telegram Chat ID. |
|PAUSADO |✅| Umbral de torrents con el estado en pausa para enviar la notificación a Telegram. |
|NO_TRACKER |✅| Umbral de torrents con el estado tracker "Not working" para enviar la notificación a Telegram. |
|NOMBRE |✅| Incluir nombre/s de torrent/s afectados en la notificación a Telegram. (0 = No / 1 = Si) |
|RESUMEN |✅| Incluye un resumen con el estado de todos los torrents en la notificación a Telegram. (0 = No / 1 = Si) |
|CRON |✅| Hora / fecha de ejecución. (formato crontab. ej., 0 7 * * * = cada día a las 7:00 AM, visita https://crontab.guru/ para más info. |
|DEBUG |✅| Habilita el modo Debug en el log. (0 = No / 1 = Si) |
|TZ |✅| Timezone (Por ejemplo: Europe/Madrid) |

---

## Ejemplo docker-compose.yml
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
### Instalación plantilla en Unraid.

- Nos vamos a una ventana de terminal en nuestro Unraid, pegamos esta línea y enter:
```sh
wget -O /boot/config/plugins/dockerMan/templates-user/my-check-torrents-client.xml https://raw.githubusercontent.com/unraiders/check-torrents-client/refs/heads/main/my-check-torrents-client.xml
```
- Nos vamos a DOCKER y abajo a la izquierda tenemos el botón "AGREGAR CONTENEDOR" hacemos click y en seleccionar plantilla seleccionamos check-torrents-client y rellenamos las variables de entorno necesarias, tienes una explicación en cada variable en la propia plantilla.

---

  > [!TIP]
  > Funcionando en qBittorrent v4.6.5 y Transmission v4.0.5, es posible que funcione en versiones posteriores.

---



