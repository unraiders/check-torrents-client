from check_torrents_client_config import get_synology_ds_client
from config import NO_TRACKER, NOMBRE, PAUSADO, RESUMEN, RESUMEN_TRACKERS
from send_torrents_telegram import generar_resumen, generar_resumen_trackers, send_telegram_message
from utils import setup_logger

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
    tracker_stats = {}
    total_torrents = 0

    torrents = client.tasks_list()

    for torrent in torrents["data"]["tasks"]:
        total_torrents += 1
        logger.debug(f"Procesando torrent: {torrent['title']}")

        # Estados base del torrent
        syno_paused_states = ["paused"]
        syno_error_states = ["error"]
        syno_working_states = ["seeding", "downloading"]
        syno_finished_states = ["finished"]

        # Procesar estado del torrent
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

        # Procesar trackers
        info = client.tasks_info(task_id=torrent["id"], additional_param="tracker")
        if "data" in info and "tasks" in info["data"]:
            for task in info["data"]["tasks"]:
                if "additional" in task and "tracker" in task["additional"]:
                    trackers = task["additional"]["tracker"]
                    for tracker in trackers:
                        # Procesar estadísticas de tracker
                        try:
                            from urllib.parse import urlparse
                            parsed_url = urlparse(tracker.get("url", ""))
                            domain = parsed_url.netloc
                            if ':' in domain:
                                domain = domain.split(':')[0]
                            if domain.startswith('www.'):
                                domain = domain[4:]
                            if domain and domain not in ['[dht]', '[pex]', '[lsd]']:
                                if domain not in tracker_stats:
                                    tracker_stats[domain] = 0
                                tracker_stats[domain] += 1
                        except (ValueError, AttributeError) as e:
                            logger.error(f"Error procesando tracker URL '{parsed_url}': {e}")
                            continue

                        # Solo procesar estado del tracker si el torrent no está en estados finales
                        if torrent["status"] not in syno_paused_states + syno_finished_states:
                            if tracker["status"] == 4:  # Not working
                                stats["not_working"].append(torrent)
                                logger.debug(f"Torrent con tracker not working: {torrent['title']}")
                                break
                            elif tracker["status"] == 3:  # Updating
                                stats["updating"].append(torrent)
                                logger.debug(f"Torrent con tracker updating: {torrent['title']}")
                                break
                            elif tracker["status"] == 2:  # Working
                                stats["working"].append(torrent)
                                logger.debug(f"Torrent con tracker working: {torrent['title']}")
                                break
                            elif tracker["status"] == 1:  # Not connected
                                stats["not_connect"].append(torrent)
                                logger.debug(f"Torrent con tracker not connect: {torrent['title']}")
                                break

    logger.info(f"Procesados {total_torrents} torrents en total")
    return stats, tracker_stats, total_torrents


def go_torrents_synology_ds():
    logger.info("Iniciando proceso de torrents en Synology Download Station")
    torrent_stats, tracker_stats, total_torrents = get_torrent_stats()
    messages = []

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
            messages.append(message)
            logger.info(f"Preparada notificación de {paused_count} torrents pausados")

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
            messages.append(message)
            logger.info(f"Preparada notificación de {not_working_count} torrents con trackers not working")

    if RESUMEN and (PAUSADO > 0 or NO_TRACKER > 0):
        logger.info("Preparando resumen de estado")
        message = generar_resumen(torrent_stats, "Synology Download Station", return_message=True)
        messages.append(message)

    if RESUMEN_TRACKERS:
        logger.info("Preparando resumen de trackers")
        message = generar_resumen_trackers(tracker_stats, "Synology Download Station", total_torrents, return_message=True)
        messages.append(message)

    if messages:
        final_message = "\n\n".join(messages)
        send_telegram_message(final_message)


