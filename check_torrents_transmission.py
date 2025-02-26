import time

import telebot

from check_torrents_client_config import get_transmission_client
from config import DEBUG, NO_TRACKER, NOMBRE, PAUSADO, RESUMEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils import setup_logger

# Inicializa el bot con el token
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

logger = setup_logger(__name__)


def get_torrent_stats():
    client = get_transmission_client()
    logger.info("Obteniendo estadísticas de torrents")

    stats = {"paused": [], "not_working": [], "updating": [], "working": [], "not_connect": []}

    for torrent in client.get_torrents():
        logger.debug(f"Procesando torrent: {torrent.name}")
        torrent_added = False

        if torrent.status == "stopped":
            stats["paused"].append(torrent)
            logger.debug(f"Torrent en pausa: {torrent.name}")
            torrent_added = True
            continue

        if hasattr(torrent, "error") and torrent.error:
            stats["not_working"].append(torrent)
            logger.debug(f"Torrent con error: {torrent.name} - {torrent.error}")
            torrent_added = True
        elif torrent.status == "downloading" or torrent.status == "seeding":
            stats["working"].append(torrent)
            logger.debug(f"Torrent working: {torrent.name}")
            torrent_added = True
        elif torrent.status in ["check pending", "checking"]:
            stats["updating"].append(torrent)
            logger.debug(f"Torrent updating: {torrent.name}")
            torrent_added = True

        if not torrent_added:
            if hasattr(torrent, "tracker_stats") and torrent.tracker_stats:
                has_working_tracker = False
                for tracker in torrent.tracker_stats:
                    if hasattr(tracker, "has_announced") and tracker.has_announced:
                        stats["working"].append(torrent)
                        has_working_tracker = True
                        logger.debug(f"Torrent con tracker working: {torrent.name}")
                        break
                    elif (
                        hasattr(tracker, "last_announce_peer_count")
                        and tracker.last_announce_peer_count > 0
                    ):
                        stats["working"].append(torrent)
                        has_working_tracker = True
                        logger.debug(f"Torrent con peers activos: {torrent.name}")
                        break
                if not has_working_tracker:
                    stats["not_connect"].append(torrent)
                    logger.debug(f"Torrent con tracker not connect: {torrent.name}")
            else:
                stats["not_connect"].append(torrent)
                logger.debug(f"Torrent sin trackers: {torrent.name}")

    for key in stats:
        stats[key] = list(dict.fromkeys(stats[key]))

    logger.info(f"Procesados {sum(len(lista) for lista in stats.values())} torrents en total")
    return stats


def go_torrents_transmission():
    logger.info("Iniciando proceso de torrents en Transmission")
    torrent_stats = get_torrent_stats()

    if PAUSADO > 0:
        paused_count = len(torrent_stats["paused"])
        logger.debug(f"Encontrados {paused_count} torrents pausados")

        if paused_count >= PAUSADO:
            message = f"<b>Hay {paused_count} torrents en pausa, parados o con error.</b>"
            if NOMBRE:
                for torrent in torrent_stats["paused"]:
                    logger.debug(f"Torrent pausado: {torrent.name}")
                torrent_names = "\n\n🟠 ".join(torrent.name for torrent in torrent_stats["paused"])
                message += f"\n\n🟠 {torrent_names}"
            send_telegram_message(message)
            logger.info(f"Enviada notificación de {paused_count} torrents pausados")

    if NO_TRACKER > 0:
        not_working_count = len(torrent_stats["not_working"])
        logger.debug(f"Encontrados {not_working_count} torrents con trackers not working")

        if not_working_count >= NO_TRACKER:
            message = f'<b>Hay {not_working_count} torrents con trackers "Not working".</b>'
            if NOMBRE:
                for torrent in torrent_stats["not_working"]:
                    logger.debug(f"Torrent con tracker not working: {torrent.name}")
                torrent_names = "\n\n🔴 ".join(
                    torrent.name for torrent in torrent_stats["not_working"]
                )
                message += f"\n\n🔴 {torrent_names}"
            send_telegram_message(message)
            logger.info(
                f"Enviada notificación de {not_working_count} torrents con trackers not working"
            )

    if RESUMEN and (PAUSADO > 0 or NO_TRACKER > 0):
        logger.info("Generando resumen de estado")
        generar_resumen(torrent_stats)


def generar_resumen(stats):
    logger.debug("Preparando mensaje de resumen")
    message = "<b>📝 Resumen Transmission</b>"
    message_paused = f"Hay {len(stats['paused'])} torrents en pausa, parados o con error"
    message_updating = f'Hay {len(stats["updating"])} torrents con trackers "Updating"'
    message_working = f'Hay {len(stats["working"])} torrents con trackers "Working"'
    message_not_connect = f'Hay {len(stats["not_connect"])} torrents con trackers "Not connect"'
    message_not_working = f'Hay {len(stats["not_working"])} torrents con trackers "Not working"'

    message_resumen = (
        f"{message}\n"
        f"🟠 {message_paused}\n"
        f"🟡 {message_updating}\n"
        f"🟢 {message_working}\n"
        f"🔵 {message_not_connect}\n"
        f"🔴 {message_not_working}"
    )

    logger.info("Enviando resumen de estado")
    send_telegram_message(message_resumen)

    for key, torrents in stats.items():
        logger.debug(f"Estado {key}: {len(torrents)} torrents")
        if DEBUG:
            for torrent in torrents:
                logger.debug(f"  - {torrent.name}")


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

    except Exception as e:
        logger.error(f"Error al enviar mensaje a Telegram: {str(e)}")
