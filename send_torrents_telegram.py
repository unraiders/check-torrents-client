import time

import telebot

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils import setup_logger

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

logger = setup_logger(__name__)

def split_message(message, max_length=4000):
    """Divide un mensaje largo en partes más pequeñas, max. Telegram 4096"""
    if len(message) <= max_length:
        return [message]

    parts = []
    current_part = ""
    lines = message.split("\n")

    for line in lines:
        if len(current_part) + len(line) + 1 <= max_length:
            current_part += line + "\n"
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = line + "\n"

    if current_part:
        parts.append(current_part.strip())

    return parts

def send_telegram_message(message):
    """Envía mensajes a Telegram, dividiendo mensajes largos si es necesario."""
    try:
        message_parts = split_message(message)

        for part in message_parts:
            bot.send_message(TELEGRAM_CHAT_ID, part, parse_mode="HTML")
            if len(message_parts) > 1:
                time.sleep(1)
            logger.info("Todo listo!!, esperando a la siguiente programación")

    except Exception as e:
        logger.error(f"Error al enviar mensaje a Telegram: {str(e)}")

def generar_resumen(stats, client_name, return_message=False):
    """Genera y envía un resumen del estado de los torrents."""
    logger.debug("Preparando mensaje de resumen")
    message = f"<b>📝 Resumen torrents en {client_name}</b>"
    message_paused = f"Hay {len(stats['paused'])} torrents en pausa, parados o con error"
    message_updating = f'Hay {len(stats["updating"])} torrents con trackers "Updating"'
    message_working = f'Hay {len(stats["working"])} torrents con trackers "Working"'
    message_not_connect = f'Hay {len(stats["not_connect"])} torrents con trackers "Not connect"'
    message_not_working = f'Hay {len(stats["not_working"])} torrents con trackers "Not working"'

    message_resumen = (
        f"{message}\n\n"
        f"🟠 {message_paused}\n"
        f"🟡 {message_updating}\n"
        f"🟢 {message_working}\n"
        f"🔵 {message_not_connect}\n"
        f"🔴 {message_not_working}"
    )

    # Agregar información de torrents completados si existe (Synology)
    if 'finished' in stats:
        message_finished = f"Hay {len(stats['finished'])} torrents completados"
        message_resumen += f"\n🟣 {message_finished}"

    logger.info("Enviando resumen de estado")

    if return_message:
        return message_resumen
    else:
        send_telegram_message(message_resumen)

def generar_resumen_trackers(tracker_stats, client_name, total_torrents=None, return_message=False):
    """Genera y envía un resumen de los torrents por tracker."""
    logger.debug("Preparando mensaje de resumen de trackers")
    message = f"<b>📊 Resumen trackers en {client_name}</b>\n"

    # Ordenar trackers por cantidad de torrents (de mayor a menor)
    sorted_trackers = sorted(tracker_stats.items(), key=lambda x: x[1], reverse=True)

    for domain, count in sorted_trackers:
        message += f"\n🏴‍☠️ {domain}: {count} torrents"

    if total_torrents:
        message += f"\n\n📈 Total: {total_torrents} torrents"

    logger.info("Enviando resumen de trackers")

    if return_message:
        return message
    else:
        send_telegram_message(message)
