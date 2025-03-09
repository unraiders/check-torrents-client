from check_torrents_client_config import get_transmission_client
from config import NO_TRACKER, NOMBRE, PAUSADO, RESUMEN, RESUMEN_TRACKERS
from send_torrents_telegram import generar_resumen, generar_resumen_trackers, send_telegram_message
from utils import setup_logger

logger = setup_logger(__name__)

def get_torrent_stats():
    client = get_transmission_client()
    logger.info("Obteniendo estadísticas de torrents")

    stats = {"paused": [], "not_working": [], "updating": [], "working": [], "not_connect": []}
    tracker_stats = {}
    ignored_trackers = ['[dht]', '[pex]', '[lsd]']
    total_torrents = 0

    for torrent in client.get_torrents():
        total_torrents += 1
        logger.debug(f"Procesando torrent: {torrent.name}")

        # Procesar estado del torrent
        is_paused = torrent.status == "stopped"
        if is_paused:
            stats["paused"].append(torrent)
            logger.debug(f"Torrent en pausa: {torrent.name}")

        # Procesar trackers para estadísticas
        if hasattr(torrent, "trackers"):
            for tracker in torrent.trackers:
                tracker_url = tracker.get("announce", "").lower()
                if not any(ignored in tracker_url.lower() for ignored in ignored_trackers):
                    try:
                        from urllib.parse import urlparse
                        parsed_url = urlparse(tracker_url)
                        domain = parsed_url.netloc
                        if ':' in domain:
                            domain = domain.split(':')[0]
                        if domain.startswith('www.'):
                            domain = domain[4:]
                        if domain:
                            if domain not in tracker_stats:
                                tracker_stats[domain] = 0
                            tracker_stats[domain] += 1
                    except (ValueError, AttributeError) as e:
                        logger.error(f"Error procesando tracker URL '{tracker_url}': {e}")
                        continue

        # Solo procesar estado del tracker si no está pausado
        if not is_paused:
            if hasattr(torrent, "error") and torrent.error:
                stats["not_working"].append(torrent)
                logger.debug(f"Torrent con error: {torrent.name} - {torrent.error}")
            elif torrent.status in ["check pending", "checking"]:
                stats["updating"].append(torrent)
                logger.debug(f"Torrent updating: {torrent.name}")
            elif torrent.status in ["downloading", "seeding"]:
                stats["working"].append(torrent)
                logger.debug(f"Torrent working: {torrent.name}")
            elif hasattr(torrent, "tracker_stats") and torrent.tracker_stats:
                has_working_tracker = False
                for tracker in torrent.tracker_stats:
                    if (hasattr(tracker, "has_announced") and tracker.has_announced) or \
                       (hasattr(tracker, "last_announce_peer_count") and tracker.last_announce_peer_count > 0):
                        stats["working"].append(torrent)
                        has_working_tracker = True
                        logger.debug(f"Torrent con tracker working: {torrent.name}")
                        break
                if not has_working_tracker:
                    stats["not_connect"].append(torrent)
                    logger.debug(f"Torrent con tracker not connect: {torrent.name}")
            else:
                stats["not_connect"].append(torrent)
                logger.debug(f"Torrent sin trackers: {torrent.name}")

    # Eliminar duplicados
    for key in stats:
        stats[key] = list(dict.fromkeys(stats[key]))

    logger.info(f"Procesados {total_torrents} torrents en total")
    return stats, tracker_stats, total_torrents

def go_torrents_transmission():
    logger.info("Iniciando proceso de torrents en Transmission")
    torrent_stats, tracker_stats, total_torrents = get_torrent_stats()
    messages = []

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
            messages.append(message)
            logger.info(f"Preparada notificación de {paused_count} torrents pausados")

    if NO_TRACKER > 0:
        not_working_count = len(torrent_stats["not_working"])
        logger.debug(f"Encontrados {not_working_count} torrents con trackers not working")

        if not_working_count >= NO_TRACKER:
            message = f'<b>Hay {not_working_count} torrents con trackers "Not working".</b>'
            if NOMBRE:
                for torrent in torrent_stats["not_working"]:
                    logger.debug(f"Torrent con tracker not working: {torrent.name}")
                torrent_names = "\n\n🔴 ".join(torrent.name for torrent in torrent_stats["not_working"])
                message += f"\n\n🔴 {torrent_names}"
            messages.append(message)
            logger.info(f"Preparada notificación de {not_working_count} torrents not working")

    if RESUMEN and (PAUSADO > 0 or NO_TRACKER > 0):
        logger.info("Preparando resumen de estado")
        message = generar_resumen(torrent_stats, "Transmission", return_message=True)
        messages.append(message)

    if RESUMEN_TRACKERS:
        logger.info("Preparando resumen de trackers")
        message = generar_resumen_trackers(tracker_stats, "Transmission", total_torrents, return_message=True)
        messages.append(message)

    if messages:
        final_message = "\n\n".join(messages)
        send_telegram_message(final_message)


