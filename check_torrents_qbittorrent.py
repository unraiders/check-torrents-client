from check_torrents_client_config import get_qbittorrent_client
from config import AGRUPACION, MISSING_FILES, NO_TRACKER, NOMBRE, PAUSADO, RESUMEN, RESUMEN_TRACKERS
from send_torrents_client import generar_resumen, generar_resumen_trackers, send_client_message
from utils import format_torrents_agrupados, get_tracker_domain, setup_logger

logger = setup_logger(__name__)

def get_torrent_stats():
    client = get_qbittorrent_client()
    logger.info("Obteniendo estadísticas de torrents")

    stats = {"paused": [], "not_working": [], "updating": [], "working": [], "not_connect": [], "missing_files": []}
    tracker_stats = {}
    ignored_trackers = ['[dht]', '[pex]', '[lsd]']
    total_torrents = 0

    for torrent in client.torrents_info():
        total_torrents += 1
        logger.debug(f"Procesando torrent: {torrent.name}")

        # Obtener trackers del torrent
        trackers = client.torrents_trackers(torrent.hash)
        
        # Obtener el dominio del primer tracker válido para agrupación
        torrent_tracker_domain = "Desconocido"
        for tracker in trackers:
            tracker_url = tracker.get("url", "").lower()
            if not any(ignored in tracker_url for ignored in ignored_trackers):
                torrent_tracker_domain = get_tracker_domain(tracker_url)
                if torrent_tracker_domain and torrent_tracker_domain != "Desconocido":
                    break

        # Procesar estado del torrent
        is_paused = torrent.state in ["pausedUP", "pausedDL", "stoppedUP", "stoppedDL", "error", "unknown"]
        if is_paused:
            stats["paused"].append((torrent.name, torrent_tracker_domain))
            logger.debug(f"Torrent en pausa: {torrent.name}")
            
        # Detectar archivos faltantes
        if torrent.state == "missingFiles":
            stats["missing_files"].append((torrent.name, torrent_tracker_domain))
            logger.debug(f"Torrent con archivos faltantes: {torrent.name}")

        # Procesar estadísticas de tracker independientemente del estado
        for tracker in trackers:
            tracker_url = tracker.get("url", "").lower()
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

        # Solo procesar estado del tracker si el torrent no está pausado
        if not is_paused:
            tracker_processed = False
            for tracker in trackers:
                if not tracker_processed:
                    if tracker["status"] == 4:
                        stats["not_working"].append((torrent.name, torrent_tracker_domain))
                        logger.debug(f"Torrent con tracker not working: {torrent.name}")
                        tracker_processed = True
                    elif tracker["status"] == 3:
                        stats["updating"].append((torrent.name, torrent_tracker_domain))
                        logger.debug(f"Torrent con tracker updating: {torrent.name}")
                        tracker_processed = True
                    elif tracker["status"] == 2:
                        stats["working"].append((torrent.name, torrent_tracker_domain))
                        logger.debug(f"Torrent con tracker working: {torrent.name}")
                        tracker_processed = True
                    elif tracker["status"] == 1:
                        stats["not_connect"].append((torrent.name, torrent_tracker_domain))
                        logger.debug(f"Torrent con tracker not connect: {torrent.name}")
                        tracker_processed = True

    logger.info(f"Procesados {total_torrents} torrents en total")
    return stats, tracker_stats, total_torrents

def go_torrents_qbittorrent():
    logger.info("Iniciando proceso de torrents en qBittorrent")
    torrent_stats, tracker_stats, total_torrents = get_torrent_stats()
    messages = []

    if PAUSADO > 0:
        paused_count = len(torrent_stats["paused"])
        logger.debug(f"Encontrados {paused_count} torrents pausados")

        if paused_count >= PAUSADO:
            message = f"<b>Hay {paused_count} torrents en pausa, parados o con error.</b>"
            if NOMBRE:
                for nombre, tracker in torrent_stats["paused"]:
                    logger.debug(f"Torrent pausado: {nombre}")
                if AGRUPACION:
                    message += format_torrents_agrupados(torrent_stats["paused"], "🟠")
                else:
                    torrent_names = "\n\n🟠 ".join(nombre for nombre, tracker in torrent_stats["paused"])
                    message += f"\n\n🟠 {torrent_names}"
            messages.append(message)
            logger.info(f"Preparada notificación de {paused_count} torrents pausados")

    if NO_TRACKER > 0:
        not_working_count = len(torrent_stats["not_working"])
        logger.debug(f"Encontrados {not_working_count} torrents con trackers not working")

        if not_working_count >= NO_TRACKER:
            message = f'<b>Hay {not_working_count} torrents con trackers "Not working".</b>'
            if NOMBRE:
                for nombre, tracker in torrent_stats["not_working"]:
                    logger.debug(f"Torrent con tracker not working: {nombre}")
                if AGRUPACION:
                    message += format_torrents_agrupados(torrent_stats["not_working"], "🔴")
                else:
                    torrent_names = "\n\n🔴 ".join(
                        nombre for nombre, tracker in torrent_stats["not_working"]
                    )
                    message += f"\n\n🔴 {torrent_names}"
            messages.append(message)
            logger.info(f"Preparada notificación de {not_working_count} torrents not working")
            
    if MISSING_FILES > 0:
        missing_files_count = len(torrent_stats["missing_files"])
        logger.debug(f"Encontrados {missing_files_count} torrents con archivos faltantes")
        
        if missing_files_count >= MISSING_FILES:
            message = f"<b>Hay {missing_files_count} torrents con archivos faltantes.</b>"
            if NOMBRE:
                for nombre, tracker in torrent_stats["missing_files"]:
                    logger.debug(f"Torrent con archivos faltantes: {nombre}")
                if AGRUPACION:
                    message += format_torrents_agrupados(torrent_stats["missing_files"], "🟣")
                else:
                    torrent_names = "\n\n🟣 ".join(
                        nombre for nombre, tracker in torrent_stats["missing_files"]
                    )
                    message += f"\n\n🟣 {torrent_names}"
            messages.append(message)
            logger.info(f"Preparada notificación de {missing_files_count} torrents con archivos faltantes")

    if RESUMEN and (PAUSADO > 0 or NO_TRACKER > 0 or MISSING_FILES > 0):
        logger.info("Preparando resumen de estado")
        message = generar_resumen(torrent_stats, "qBittorrent", return_message=True)
        messages.append(message)

    if RESUMEN_TRACKERS:
        logger.info("Preparando resumen de trackers")
        message = generar_resumen_trackers(tracker_stats, "qBittorrent", total_torrents, return_message=True)
        messages.append(message)

    if messages:
        final_message = "\n\n".join(messages)
        send_client_message(final_message)
