import html
import time

from check_torrents_client_config import get_qbittorrent_client
from config import (
    AGRUPACION,
    MENSAJE_EXTENDIDO,
    MISSING_FILES,
    NO_TRACKER,
    NOMBRE,
    PAUSADO,
    REANUNCIO,
    REANUNCIO_ESPERA,
    RESUMEN,
    RESUMEN_TRACKERS,
)
from send_torrents_client import generar_resumen, generar_resumen_trackers, send_client_message
from utils import (
    format_torrents_agrupados,
    format_torrents_lista,
    get_tracker_domain,
    setup_logger,
)

logger = setup_logger(__name__)

# Estados de tracker considerados "Not working". qBittorrent 5.2 (Web API 2.15.1)
# desglosó el antiguo estado 4 en 4 (Not working), 5 (Tracker error) y 6 (Unreachable).
TRACKER_STATUS_NOT_WORKING = (4, 5, 6)

# Estados de tracker conocidos, para avisar si qBittorrent devuelve alguno nuevo.
TRACKER_STATUS_CONOCIDOS = (0, 1, 2, 3, 4, 5, 6)

# Entradas que qBittorrent devuelve junto a los trackers reales y que no se valoran.
IGNORED_TRACKERS = ['[dht]', '[pex]', '[lsd]']

# Estados de torrent que se notifican como "en pausa, parados o con error",
# con el motivo concreto que se muestra junto a cada nombre.
ESTADOS_PAUSADOS = {
    "stoppedUP": "parado",
    "stoppedDL": "parado",
    "pausedUP": "parado",
    "pausedDL": "parado",
    "error": "error",
    "unknown": "desconocido",
}

# Longitud máxima del mensaje del tracker que se muestra en la notificación.
MAX_LONGITUD_MSG = 80


def trackers_reales(trackers):
    """Descarta las entradas [DHT], [PeX] y [LSD] y devuelve solo los trackers del torrent."""
    return [
        tracker
        for tracker in trackers
        if not any(ignored in tracker.get("url", "").lower() for ignored in IGNORED_TRACKERS)
    ]


def clasificar_trackers(trackers, torrent_name=""):
    """
    Determina la categoría de un torrent según el estado de sus trackers.

    Se evalúan todos los trackers reales, igual que hace la interfaz de qBittorrent:
    basta con que uno funcione para no dar el torrent por caído.

    Args:
        trackers: Lista de trackers del torrent
        torrent_name: Nombre del torrent, solo para el log

    Returns:
        str: Categoría del torrent o None si no se puede determinar
    """
    estados = []
    for tracker in trackers_reales(trackers):
        estado = tracker["status"]
        estados.append(estado)
        if estado not in TRACKER_STATUS_CONOCIDOS:
            logger.warning(
                f"Estado de tracker desconocido ({estado}) en {torrent_name}, "
                f"revisar si qBittorrent ha añadido estados nuevos"
            )

    if 2 in estados:
        return "working"
    if 3 in estados:
        return "updating"
    if any(estado in TRACKER_STATUS_NOT_WORKING for estado in estados):
        return "not_working"
    if 1 in estados:
        return "not_connect"
    return None


def mensaje_tracker(trackers):
    """
    Devuelve el mensaje con el que el tracker explica el fallo, listo para la notificación.

    Args:
        trackers: Lista de trackers del torrent

    Returns:
        str: Mensaje escapado y recortado, o None si ningún tracker devuelve mensaje
    """
    for tracker in trackers_reales(trackers):
        msg = str(tracker.get("msg", "")).strip()
        if msg:
            if len(msg) > MAX_LONGITUD_MSG:
                msg = f"{msg[:MAX_LONGITUD_MSG]}..."
            return html.escape(msg)
    return None


def reanunciar_torrents(client, stats, torrents_en_error):
    """
    Fuerza un reanuncio de los torrents con el tracker en error y reevalúa su estado.

    Descarta los falsos positivos pasajeros, como los trackers que rechazan el primer
    anuncio tras reiniciar el cliente. Los torrents que se recuperan salen de la
    categoría "not_working" y pasan a la que les corresponde.

    Args:
        client: Cliente de qBittorrent
        stats: Estadísticas de torrents, se modifican en el sitio
        torrents_en_error: Lista de tuplas (hash, min_announce) de los torrents en error
    """
    ahora = time.time()

    # Se respeta el intervalo mínimo que pide el tracker para no insistir antes de tiempo.
    hashes = [hash_torrent for hash_torrent, min_announce in torrents_en_error if min_announce <= ahora]
    esperando = len(torrents_en_error) - len(hashes)
    if esperando:
        logger.debug(f"{esperando} torrents no se reanuncian todavía, su tracker pide esperar")
    if not hashes:
        return

    logger.info(f"Reanunciando {len(hashes)} torrents con el tracker en error")
    client.torrents_reannounce(torrent_hashes=hashes)
    time.sleep(REANUNCIO_ESPERA)

    recuperados = {}
    for torrent in client.torrents_info(torrent_hashes=hashes, include_trackers=True):
        trackers = torrent.get("trackers") or client.torrents_trackers(torrent.hash)
        categoria = clasificar_trackers(trackers, torrent.name)
        if categoria and categoria != "not_working":
            recuperados[torrent.hash] = categoria
            logger.debug(f"Torrent recuperado tras el reanuncio ({categoria}): {torrent.name}")

    if not recuperados:
        logger.info("Ningún torrent se ha recuperado tras el reanuncio")
        return

    pendientes = []
    for (hash_torrent, _), datos in zip(torrents_en_error, stats["not_working"]):
        if hash_torrent in recuperados:
            stats[recuperados[hash_torrent]].append(datos[:2])
        else:
            pendientes.append(datos)
    stats["not_working"] = pendientes

    logger.info(f"{len(recuperados)} torrents recuperados tras el reanuncio")


def get_torrent_stats():
    client = get_qbittorrent_client()
    logger.info("Obteniendo estadísticas de torrents")

    stats = {"paused": [], "not_working": [], "updating": [], "working": [], "not_connect": [], "missing_files": []}
    tracker_stats = {}
    torrents_en_error = []
    total_torrents = 0

    # Los trackers vienen incluidos en la propia respuesta desde Web API v2.11.4,
    # lo que evita una petición por torrent. Si el servidor es anterior, se piden aparte.
    torrents = client.torrents_info(include_trackers=True)
    trackers_incluidos = bool(torrents) and "trackers" in torrents[0]
    if not trackers_incluidos:
        logger.debug("El servidor no incluye los trackers en torrents_info, se piden por torrent")

    for torrent in torrents:
        total_torrents += 1
        logger.debug(f"Procesando torrent: {torrent.name}")

        # Obtener trackers del torrent
        if trackers_incluidos:
            trackers = torrent.get("trackers") or []
        else:
            trackers = client.torrents_trackers(torrent.hash)

        # Obtener el dominio del primer tracker válido para agrupación
        torrent_tracker_domain = "Desconocido"
        for tracker in trackers_reales(trackers):
            torrent_tracker_domain = get_tracker_domain(tracker.get("url", "").lower())
            if torrent_tracker_domain and torrent_tracker_domain != "Desconocido":
                break

        # Procesar estado del torrent
        motivo_pausa = ESTADOS_PAUSADOS.get(torrent.state)
        is_paused = motivo_pausa is not None
        if is_paused:
            stats["paused"].append((torrent.name, torrent_tracker_domain, motivo_pausa))
            logger.debug(f"Torrent en pausa: {torrent.name} ({motivo_pausa})")

        # Detectar archivos faltantes
        if torrent.state == "missingFiles":
            stats["missing_files"].append((torrent.name, torrent_tracker_domain, mensaje_tracker(trackers)))
            logger.debug(f"Torrent con archivos faltantes: {torrent.name}")

        # Procesar estadísticas de tracker independientemente del estado
        for tracker in trackers_reales(trackers):
            domain = get_tracker_domain(tracker.get("url", "").lower())
            if domain and domain != "Desconocido":
                if domain not in tracker_stats:
                    tracker_stats[domain] = 0
                tracker_stats[domain] += 1

        # Solo procesar estado del tracker si el torrent no está pausado
        if not is_paused:
            categoria = clasificar_trackers(trackers, torrent.name)
            if categoria == "not_working":
                msg = mensaje_tracker(trackers)
                stats["not_working"].append((torrent.name, torrent_tracker_domain, msg))
                # El reanuncio necesita el hash y el momento a partir del cual el tracker
                # admite un nuevo anuncio.
                min_announce = max(
                    (tracker.get("min_announce") or 0) for tracker in trackers_reales(trackers)
                )
                torrents_en_error.append((torrent.hash, min_announce))
                logger.debug(f"Torrent con tracker not working: {torrent.name} ({msg})")
            elif categoria:
                stats[categoria].append((torrent.name, torrent_tracker_domain))
                logger.debug(f"Torrent con tracker {categoria}: {torrent.name}")

    logger.info(f"Procesados {total_torrents} torrents en total")

    if REANUNCIO and torrents_en_error:
        reanunciar_torrents(client, stats, torrents_en_error)

    return stats, tracker_stats, total_torrents


def detalle_visible(torrents):
    """Deja el detalle entre corchetes solo si MENSAJE_EXTENDIDO está activado."""
    if MENSAJE_EXTENDIDO:
        return torrents
    return [(nombre, tracker) for nombre, tracker, *_ in torrents]


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
                for nombre, tracker, motivo in torrent_stats["paused"]:
                    logger.debug(f"Torrent pausado: {nombre} ({motivo})")
                torrents = detalle_visible(torrent_stats["paused"])
                if AGRUPACION:
                    message += format_torrents_agrupados(torrents, "🟠")
                else:
                    message += format_torrents_lista(torrents, "🟠")
            messages.append(message)
            logger.info(f"Preparada notificación de {paused_count} torrents pausados")

    if NO_TRACKER > 0:
        not_working_count = len(torrent_stats["not_working"])
        logger.debug(f"Encontrados {not_working_count} torrents con trackers not working")

        if not_working_count >= NO_TRACKER:
            message = f'<b>Hay {not_working_count} torrents con trackers "Not working".</b>'
            if NOMBRE:
                for nombre, tracker, msg in torrent_stats["not_working"]:
                    logger.debug(f"Torrent con tracker not working: {nombre} ({msg})")
                torrents = detalle_visible(torrent_stats["not_working"])
                if AGRUPACION:
                    message += format_torrents_agrupados(torrents, "🔴")
                else:
                    message += format_torrents_lista(torrents, "🔴")
            messages.append(message)
            logger.info(f"Preparada notificación de {not_working_count} torrents not working")

    if MISSING_FILES > 0:
        missing_files_count = len(torrent_stats["missing_files"])
        logger.debug(f"Encontrados {missing_files_count} torrents con archivos faltantes")

        if missing_files_count >= MISSING_FILES:
            message = f"<b>Hay {missing_files_count} torrents con archivos faltantes.</b>"
            if NOMBRE:
                for nombre, tracker, msg in torrent_stats["missing_files"]:
                    logger.debug(f"Torrent con archivos faltantes: {nombre}")
                torrents = detalle_visible(torrent_stats["missing_files"])
                if AGRUPACION:
                    message += format_torrents_agrupados(torrents, "🟣")
                else:
                    message += format_torrents_lista(torrents, "🟣")
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
