from check_torrents_client_config import get_synology_ds_client
from config import MISSING_FILES, NO_TRACKER, NOMBRE, PAUSADO, RESUMEN, RESUMEN_TRACKERS
from send_torrents_client import generar_resumen, generar_resumen_trackers, send_client_message
from utils import setup_logger

logger = setup_logger(__name__)


def interpret_tracker_status(status):
    """
    Interpreta el estado del tracker devuelto por Synology Download Station.
    Solo maneja el caso específico de "Torrent not registered with this tracker".
    Para los demás casos, mantiene la lógica original.
    
    Args:
        status: Estado del tracker (puede ser número o texto)
    
    Returns:
        str: Estado interpretado ('not_working', 'not_connected', 'updating', 'working', 'original')
    """
    # Si es un número, usamos la lógica original (devolvemos 'original' para mantener el comportamiento anterior)
    if isinstance(status, int):
        return "original"
    
    # Si es texto, solo verificamos el mensaje específico
    if isinstance(status, str) and "torrent not registered with this tracker" in status.lower():
        return "not_working"
    
    # Para todos los demás casos (textos que no sean el mensaje específico), mantener lógica original
    return "original"


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
        "missing_files": [],
    }
    tracker_stats = {}
    total_torrents = 0

    torrents = client.tasks_list()

    for torrent in torrents["data"]["tasks"]:
        total_torrents += 1
        torrent_title = torrent['title']
        torrent_status = torrent["status"]
        logger.debug(f"Procesando torrent: {torrent_title} - Estado: {torrent_status}")

        # Estados base del torrent
        syno_paused_states = ["paused"]
        syno_error_states = ["error"]
        syno_working_states = ["seeding", "downloading"]
        syno_finished_states = ["finished"]
        
        # Variable para rastrear si el torrent ya fue categorizado
        torrent_categorized = False

        # Procesar estado del torrent (prioridad alta)
        if torrent_status in syno_paused_states:
            stats["paused"].append(torrent)
            logger.debug(f"Torrent categorizado como PAUSADO: {torrent_title}")
            torrent_categorized = True
        elif torrent_status in syno_error_states:
            stats["not_working"].append(torrent)
            logger.debug(f"Torrent categorizado como ERROR (not_working): {torrent_title}")
            torrent_categorized = True
        elif torrent_status in syno_finished_states:
            stats["finished"].append(torrent)
            logger.debug(f"Torrent categorizado como COMPLETADO: {torrent_title}")
            torrent_categorized = True

        # Verificar archivos faltantes (independiente del estado)
        info = client.tasks_info(task_id=torrent["id"], additional_param="file")
        if "data" in info and "tasks" in info["data"]:
            for task in info["data"]["tasks"]:
                if "additional" in task and "file" in task["additional"]:
                    files = task["additional"]["file"]
                    missing_files = False
                    for file_info in files:
                        if file_info.get("status") == "missing":
                            missing_files = True
                            break
                    if missing_files:
                        stats["missing_files"].append(torrent)
                        logger.debug(f"Torrent con archivos faltantes: {torrent_title}")

        # Procesar trackers solo si el torrent está activo (no pausado, no terminado, no en error)
        if not torrent_categorized and torrent_status in syno_working_states:
            info = client.tasks_info(task_id=torrent["id"], additional_param="tracker")
            if "data" in info and "tasks" in info["data"]:
                for task in info["data"]["tasks"]:
                    if "additional" in task and "tracker" in task["additional"]:
                        trackers = task["additional"]["tracker"]
                        tracker_status_found = None
                        
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
                                logger.error(f"Error procesando tracker URL: {e}")
                                continue

                            # Obtener el estado de tracker (puede ser texto o número)
                            tracker_status = tracker.get("status")
                            logger.debug(f"  Tracker: {tracker.get('url', 'N/A')} - Estado: {tracker_status}")
                            
                            # Interpretar el estado del tracker
                            interpreted_status = interpret_tracker_status(tracker_status)
                            
                            if interpreted_status == "not_working":  # Mensaje específico detectado
                                tracker_status_found = "not_working"
                                break  # No necesitamos seguir buscando
                            elif interpreted_status == "original":  # Usar lógica original para números
                                if tracker_status == 4:  # Not working (peor estado)
                                    tracker_status_found = "not_working"
                                    break
                                elif tracker_status == 1 and tracker_status_found != "not_working":  # Not connected
                                    tracker_status_found = "not_connected"
                                elif tracker_status == 3 and tracker_status_found not in ["not_working", "not_connected"]:  # Updating
                                    tracker_status_found = "updating"
                                elif tracker_status == 2 and tracker_status_found is None:  # Working
                                    tracker_status_found = "working"

                        # Categorizar según el peor estado de tracker encontrado
                        if tracker_status_found == "not_working":
                            stats["not_working"].append(torrent)
                            logger.debug(f"Torrent categorizado como NOT WORKING: {torrent_title}")
                        elif tracker_status_found == "not_connected":
                            stats["not_connect"].append(torrent)
                            logger.debug(f"Torrent categorizado como NOT CONNECTED: {torrent_title}")
                        elif tracker_status_found == "updating":
                            stats["updating"].append(torrent)
                            logger.debug(f"Torrent categorizado como UPDATING: {torrent_title}")
                        elif tracker_status_found == "working":
                            stats["working"].append(torrent)
                            logger.debug(f"Torrent categorizado como WORKING: {torrent_title}")
                        else:
                            # Si no encontramos estados de tracker, lo categorizamos como working por defecto
                            stats["working"].append(torrent)
                            logger.debug(f"Torrent categorizado como WORKING (por defecto): {torrent_title}")

    logger.info(f"Procesados {total_torrents} torrents en total")
    
    # Log del resumen de categorización
    logger.debug(f"Resumen de categorización:")
    logger.debug(f"  - Pausados: {len(stats['paused'])}")
    logger.debug(f"  - Not Working: {len(stats['not_working'])}")
    logger.debug(f"  - Not Connected: {len(stats['not_connect'])}")
    logger.debug(f"  - Updating: {len(stats['updating'])}")
    logger.debug(f"  - Working: {len(stats['working'])}")
    logger.debug(f"  - Finished: {len(stats['finished'])}")
    logger.debug(f"  - Missing Files: {len(stats['missing_files'])}")

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
            logger.debug(f"Preparada notificación de {not_working_count} torrents not working")

    if MISSING_FILES > 0:
        missing_files_count = len(torrent_stats["missing_files"])
        logger.debug(f"Encontrados {missing_files_count} torrents con archivos faltantes")
        
        if missing_files_count >= MISSING_FILES:
            message = f"<b>Hay {missing_files_count} torrents con archivos faltantes.</b>"
            if NOMBRE:
                for torrent in torrent_stats["missing_files"]:
                    logger.debug(f"Torrent con archivos faltantes: {torrent['title']}")
                torrent_names = "\n\n🟣 ".join(torrent["title"] for torrent in torrent_stats["missing_files"])
                message += f"\n\n🟣 {torrent_names}"
            messages.append(message)
            logger.debug(f"Preparada notificación de {missing_files_count} torrents con archivos faltantes")

    if RESUMEN and (PAUSADO > 0 or NO_TRACKER > 0 or MISSING_FILES > 0):
        logger.info("Preparando resumen de estado")
        message = generar_resumen(torrent_stats, "Synology Download Station", return_message=True)
        messages.append(message)

    if RESUMEN_TRACKERS:
        logger.info("Preparando resumen de trackers")
        message = generar_resumen_trackers(tracker_stats, "Synology Download Station", total_torrents, return_message=True)
        messages.append(message)

    if messages:
        final_message = "\n\n".join(messages)
        send_client_message(final_message)



