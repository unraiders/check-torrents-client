FROM python:3.12-alpine

LABEL maintainer="unraiders"
LABEL description="Comprobar los torrents con estado no-tracker, pausados o con error en los clientes qBittorrent y Transmission con notificaciones a Telegram"

RUN apk add --no-cache dcron mc

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

COPY VERSION.txt /app/VERSION.txt
ARG VERSION=$(cat /app/VERSION.txt)
ENV VERSION=${VERSION}


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

# Set ownership of all files
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
