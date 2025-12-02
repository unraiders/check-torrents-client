from check_torrents_client_config import get_transmission_client
from config import AGRUPACION, MISSING_FILES, NO_TRACKER, NOMBRE, PAUSADO, RESUMEN, RESUMEN_TRACKERS
from send_torrents_client import generar_resumen, generar_resumen_trackers, send_client_message
from utils import format_torrents_agrupados, get_tracker_domain, setup_logger

logger = setup_logger(__name__)

def get_torrent_stats():
    client = get_transmission_client()
    logger.info("Obteniendo estadísticas de torrents")

    stats = {"paused": [], "not_working": [], "updating": [], "working": [], "not_connect": [], "missing_files": []}
    tracker_stats = {}
    ignored_trackers = ['[dht]', '[pex]', '[lsd]']
    total_torrents = 0

    for torrent in client.get_torrents():
        total_torrents += 1
        logger.debug(f"Procesando torrent: {torrent.name}")

        # Obtener el dominio del primer tracker válido para agrupación
        torrent_tracker_domain = "Desconocido"
        if hasattr(torrent, "trackers"):
            for tracker in torrent.trackers:
                tracker_url = tracker.get("announce", "").lower()
                if not any(ignored in tracker_url for ignored in ignored_trackers):
                    torrent_tracker_domain = get_tracker_domain(tracker_url)
                    if torrent_tracker_domain and torrent_tracker_domain != "Desconocido":
                        break

        # Primero detectamos archivos faltantes, independientemente del estado
        has_missing_files = False
        
        # Verificamos por errores usando error_string (que contiene el mensaje de error legible)
        if hasattr(torrent, "error_string") and torrent.error_string:
            error_msg = torrent.error_string
            if "No data found!" in error_msg:
                stats["missing_files"].append((torrent.name, torrent_tracker_domain))
                has_missing_files = True
                logger.debug(f"Torrent con archivos faltantes: {torrent.name} - Error: {error_msg}")
        # Como respaldo, también verificamos la propiedad error
        elif hasattr(torrent, "error") and torrent.error != 0:
            error_msg = str(torrent.error)
            if "No data found!" in error_msg:
                stats["missing_files"].append((torrent.name, torrent_tracker_domain))
                has_missing_files = True
                logger.debug(f"Torrent con archivos faltantes: {torrent.name} - Error: {error_msg}")
        
        # Procesamos el estado del torrent, pero no añadimos a "paused" los que ya añadimos a "missing_files"
        is_paused = torrent.status == "stopped"
        if is_paused and not has_missing_files:
            stats["paused"].append((torrent.name, torrent_tracker_domain))
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

        # Solo procesar estado del tracker si no está pausado y no tiene archivos faltantes
        if not is_paused and not has_missing_files:
            # Aquí procesamos otros errores que no sean de archivos faltantes
            if hasattr(torrent, "error_string") and torrent.error_string:
                if "No data found!" not in torrent.error_string:
                    stats["not_working"].append((torrent.name, torrent_tracker_domain))
                    logger.debug(f"Torrent con error: {torrent.name} - {torrent.error_string}")
            elif hasattr(torrent, "error") and torrent.error != 0:
                stats["not_working"].append((torrent.name, torrent_tracker_domain))
                logger.debug(f"Torrent con error: {torrent.name} - {torrent.error}")
            elif torrent.status in ["check pending", "checking"]:
                stats["updating"].append((torrent.name, torrent_tracker_domain))
                logger.debug(f"Torrent updating: {torrent.name}")
            elif torrent.status in ["downloading", "seeding"]:
                stats["working"].append((torrent.name, torrent_tracker_domain))
                logger.debug(f"Torrent working: {torrent.name}")
            elif hasattr(torrent, "tracker_stats") and torrent.tracker_stats:
                has_working_tracker = False
                for tracker in torrent.tracker_stats:
                    if (hasattr(tracker, "has_announced") and tracker.has_announced) or \
                       (hasattr(tracker, "last_announce_peer_count") and tracker.last_announce_peer_count > 0):
                        stats["working"].append((torrent.name, torrent_tracker_domain))
                        has_working_tracker = True
                        logger.debug(f"Torrent con tracker working: {torrent.name}")
                        break
                if not has_working_tracker:
                    stats["not_connect"].append((torrent.name, torrent_tracker_domain))
                    logger.debug(f"Torrent con tracker not connect: {torrent.name}")
            else:
                stats["not_connect"].append((torrent.name, torrent_tracker_domain))
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
                    torrent_names = "\n\n🔴 ".join(nombre for nombre, tracker in torrent_stats["not_working"])
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
                    torrent_names = "\n\n🟣 ".join(nombre for nombre, tracker in torrent_stats["missing_files"])
                    message += f"\n\n🟣 {torrent_names}"
            messages.append(message)
            logger.info(f"Preparada notificación de {missing_files_count} torrents con archivos faltantes")

    if RESUMEN and (PAUSADO > 0 or NO_TRACKER > 0 or MISSING_FILES > 0):
        logger.info("Preparando resumen de estado")
        message = generar_resumen(torrent_stats, "Transmission", return_message=True)
        messages.append(message)

    if RESUMEN_TRACKERS:
        logger.info("Preparando resumen de trackers")
        message = generar_resumen_trackers(tracker_stats, "Transmission", total_torrents, return_message=True)
        messages.append(message)

    if messages:
        final_message = "\n\n".join(messages)
        send_client_message(final_message)


