FROM python:3.12-alpine

LABEL maintainer="unraiders"
LABEL description="Comprobar los torrents con estado no-tracker, pausados o con error en los clientes qBittorrent y Transmission con notificaciones a Telegram"

ARG VERSION=1.0.1
ENV VERSION=${VERSION}

RUN apk add --no-cache dcron mc

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY check-torrents-client.py .

COPY check_torrents_client_config.py .
COPY check_torrents_qbittorrent.py .
COPY check_torrents_transmission.py .

COPY config.py .

COPY utils.py .

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
