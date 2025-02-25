#!/bin/sh

# Validar formato CRON
validar_cron() {
    if ! echo "$1" | grep -qE '^[*/0-9,-]+ [*/0-9,-]+ [*/0-9,-]+ [*/0-9,-]+ [*/0-9,-]+$'; then
        echo "Error: Formato cron inválido: $1"
        echo "Debe tener 5 campos: minuto hora día-mes mes día-semana"
        exit 1
    fi
}

# Validar que el CRON esté definido
if [ -z "$CRON" ]; then
    echo "La variable CRON no está definida."
    exit 1
fi
validar_cron "$CRON"

# Confirmación de configuración de cron
echo "$(date +'%d-%m-%Y %H:%M:%S') $VERSION - Arrancando entrypoint.sh"
echo "$(date +'%d-%m-%Y %H:%M:%S') Zona horaria: $TZ"
echo "$(date +'%d-%m-%Y %H:%M:%S') Programación CRON: $CRON"
echo "$(date +'%d-%m-%Y %H:%M:%S') Debug: $DEBUG"

# Crear una línea para cada crontab
CRON_JOB="$CRON python3 /app/check-torrents-client.py >> /proc/1/fd/1 2>> /proc/1/fd/2"

# Agregar los trabajos al crontab
echo "$CRON_JOB" > /etc/crontabs/root

# Iniciar cron en segundo plano
echo "Arrancando cron..."
crond -f -l 2 || { echo "Error arrancando cron"; exit 1; }