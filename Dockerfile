FROM python:3.12-alpine

LABEL maintainer="unraiders"
LABEL description="Comprobar los torrents con estado no-tracker, pausados o con error en los clientes qBittorrent, Transmission o Synology Download Station con notificaciones a Telegram"

ARG VERSION=1.2.0
ENV VERSION=${VERSION}
ARG LAST_ACTION="Nueva variable RESUMEN_TRACKERS para envío a Telegram del resumen de torrents por cada tracker"

RUN apk add --no-cache dcron mc

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY check-torrents-client.py .

COPY check_torrents_client_config.py .

COPY check_torrents_qbittorrent.py .
COPY check_torrents_transmission.py .
COPY check_torrents_synology_ds.py .
COPY send_torrents_telegram.py .

COPY config.py .

COPY utils.py .

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
