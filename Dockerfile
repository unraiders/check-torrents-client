FROM python:3.12-alpine

LABEL maintainer="unraiders"
LABEL description="Comprobar los torrents con estado no-tracker, pausados o con error en los clientes qBittorrent, Transmission o Synology Download Station con notificaciones a Telegram o Discord"

ARG VERSION=2.0.0
ENV VERSION=${VERSION}

RUN apk add --no-cache dcron mc

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY check-torrents-client.py .

COPY check_torrents_client_config.py .

COPY check_torrents_qbittorrent.py .
COPY check_torrents_transmission.py .
COPY check_torrents_synology_ds.py .
COPY send_torrents_client.py .

COPY config.py .

COPY utils.py .

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
