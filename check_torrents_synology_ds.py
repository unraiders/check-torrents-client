import telebot

from check_torrents_client_config import get_synology_ds_client
from config import DEBUG, NO_TRACKER, NOMBRE, PAUSADO, RESUMEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils import setup_logger

# Inicializa el bot con el token
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

logger = setup_logger(__name__)


def get_torrent_stats():
    client = get_synology_ds_client()

    logger.info("Obteniendo estadísticas de torrents")

    stats = {
        "paused": [],
        "not_working": [],
        "updating": [],
        "working": [],
        "not_connect": [],
        "finished": [],
    }

    torrents = client.tasks_list()

    for torrent in torrents["data"]["tasks"]:
        logger.debug(f"Procesando torrent: {torrent['title']}")

        syno_paused_states = ["paused"]
        syno_error_states = ["error"]
        syno_working_states = ["seeding", "downloading"]
        syno_finished_states = ["finished"]

        if torrent["status"] in syno_paused_states:
            stats["paused"].append(torrent)
            logger.debug(f"Torrent en pausa: {torrent['title']}")

        elif torrent["status"] in syno_error_states:
            stats["not_working"].append(torrent)
            logger.debug(f"Torrent en error: {torrent['title']}")

        elif torrent["status"] in syno_working_states:
            stats["working"].append(torrent)
            logger.debug(f"Torrent en trabajo: {torrent['title']}")

        elif torrent["status"] in syno_finished_states:
            stats["finished"].append(torrent)
            logger.debug(f"Torrent completado: {torrent['title']}")

        info = client.tasks_info(task_id=torrent["id"], additional_param="tracker")

        if "data" in info and "tasks" in info["data"]:
            for task in info["data"]["tasks"]:
                if "additional" in task and "tracker" in task["additional"]:
                    trackers = task["additional"]["tracker"]
                    for tracker in trackers:
                        if tracker["status"] == 4:
                            stats["not_working"].append(torrent)
                            logger.debug(f"Torrent con tracker not working: {torrent['title']}")
                            break
                        elif tracker["status"] == 3:
                            stats["updating"].append(torrent)
                            logger.debug(f"Torrent con tracker updating: {torrent['title']}")
                            break
                        elif tracker["status"] == 2:
                            stats["working"].append(torrent)
                            logger.debug(f"Torrent con tracker working: {torrent['title']}")
                            break
                        elif tracker["status"] == 1:
                            stats["not_connect"].append(torrent)
                            logger.debug(f"Torrent con tracker not connect: {torrent['title']}")
                            break

    total_torrents = sum(len(lista) for lista in stats.values())
    logger.info(f"Procesados {total_torrents} torrents en total")

    for category, torrents in stats.items():
        logger.debug(f"Estado {category}: {len(torrents)} torrents")

    return stats


def go_torrents_synology_ds():
    logger.info("Iniciando proceso de torrents en Synology Download Station")
    torrent_stats = get_torrent_stats()

    if PAUSADO > 0:
        paused_count = len(torrent_stats["paused"])
        logger.debug(f"Encontrados {paused_count} torrents pausados")

        if paused_count >= PAUSADO:
            message = f"<b>Hay {paused_count} torrents en pausa, parados o con error.</b>"
            if NOMBRE:
                for torrent in torrent_stats["paused"]:
                    logger.debug(f"Torrent pausado: {torrent['title']}")
                torrent_names = "\n\n🟠 ".join(
                    torrent["title"] for torrent in torrent_stats["paused"]
                )
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
                    logger.debug(f"Torrent con tracker not working: {torrent['title']}")
                torrent_names = "\n\n🔴 ".join(
                    torrent["title"] for torrent in torrent_stats["not_working"]
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
    message = "<b>📝 Resumen Synology Download Station</b>"
    message_paused = f"Hay {len(stats['paused'])} torrents en pausa, parados o con error"
    message_updating = f'Hay {len(stats["updating"])} torrents con trackers "Updating"'
    message_working = f'Hay {len(stats["working"])} torrents con trackers "Working"'
    message_not_connect = f'Hay {len(stats["not_connect"])} torrents con trackers "Not connect"'
    message_not_working = f'Hay {len(stats["not_working"])} torrents con trackers "Not working"'
    message_finished = f"Hay {len(stats['finished'])} torrents completados"

    message_resumen = (
        f"{message}\n"
        f"🟠 {message_paused}\n"
        f"🟡 {message_updating}\n"
        f"🟢 {message_working}\n"
        f"🔵 {message_not_connect}\n"
        f"🔴 {message_not_working}\n"
        f"🟣 {message_finished}"
    )

    logger.info("Enviando resumen de estado")
    send_telegram_message(message_resumen)

    for key, torrents in stats.items():
        logger.debug(f"Estado {key}: {len(torrents)} torrents")
        if DEBUG:
            for torrent in torrents:
                logger.debug(f"  - {torrent['title']}")


def send_telegram_message(message):
    """Envía mensajes a Telegram, dividiendo mensajes largos si es necesario."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error al enviar mensaje a Telegram: {str(e)}")
