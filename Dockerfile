FROM alpine:3.22.1

LABEL maintainer="unraiders"
LABEL description="Comprobar los torrents con estado no-tracker, pausados, con error o archivos faltantes en los clientes qBittorrent, Transmission o Synology Download Station con notificaciones a Telegram o Discord"

ARG VERSION=2.3.0
ENV VERSION=$VERSION

RUN apk add --no-cache python3 py3-pip dcron mc tzdata

WORKDIR /app

COPY requirements.txt .
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt

COPY check-torrents-client.py .

COPY check_torrents_client_config.py .

COPY check_torrents_qbittorrent.py .
COPY check_torrents_transmission.py .
COPY check_torrents_synology_ds.py .
COPY send_torrents_client.py .

COPY config.py .

COPY utils.py .

COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/entrypoint.sh"]
