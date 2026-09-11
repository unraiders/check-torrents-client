import logging

from colorama import Fore, Style, init

from config import DEBUG

# Inicializar colorama
init(strip=False)  # Asegura que los códigos ANSI no se eliminen en macOS

# Definir colores para cada nivel de logging
COLORS = {
    logging.DEBUG: Fore.GREEN,
    logging.INFO: Fore.WHITE,
    logging.WARNING: Fore.YELLOW,
    logging.ERROR: Fore.RED,
    logging.CRITICAL: Fore.RED + Style.BRIGHT,
}


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        # Aplicar color según el nivel del log
        color = COLORS.get(record.levelno, Fore.WHITE)
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = ColoredFormatter(
            "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Control exhaustivo de librerías de terceros
    third_party_loggers = [
        "qbittorrentapi",
        "urllib3",
        "requests",
        "urllib3.connectionpool",
        "qbittorrentapi.decorators",
    ]

    for lib in third_party_loggers:
        lib_logger = logging.getLogger(lib)
        lib_logger.setLevel(logging.WARNING)
        lib_logger.propagate = False
        for handler in lib_logger.handlers[:]:
            lib_logger.removeHandler(handler)

    return logger


def get_tracker_domain(tracker_url):
    """
    Extrae el dominio principal de una URL de tracker.
    
    Args:
        tracker_url: URL del tracker
    
    Returns:
        str: Dominio del tracker o "Desconocido" si no se puede extraer
    """
    if not tracker_url:
        return "Desconocido"
    
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(tracker_url.lower())
        domain = parsed_url.netloc
        if ':' in domain:
            domain = domain.split(':')[0]
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain if domain else "Desconocido"
    except (ValueError, AttributeError):
        return "Desconocido"


def format_torrents_lista(torrents_con_tracker, emoji):
    """
    Formatea una lista de torrents, uno por línea.

    Args:
        torrents_con_tracker: Lista de tuplas (nombre_torrent, dominio_tracker) o
            (nombre_torrent, dominio_tracker, detalle), donde el detalle se muestra
            entre corchetes junto al nombre del torrent
        emoji: Emoji a usar para cada torrent

    Returns:
        str: Mensaje formateado con un torrent por línea
    """
    nombres = []
    for torrent in torrents_con_tracker:
        nombre = torrent[0]
        detalle = torrent[2] if len(torrent) > 2 else None
        nombres.append(f"{nombre} [{detalle}]" if detalle else nombre)

    return f"\n\n{emoji} " + f"\n\n{emoji} ".join(nombres)


def format_torrents_agrupados(torrents_con_tracker, emoji):
    """
    Formatea una lista de torrents agrupados por tracker.
    
    Args:
        torrents_con_tracker: Lista de tuplas (nombre_torrent, dominio_tracker) o
            (nombre_torrent, dominio_tracker, detalle), donde el detalle se muestra
            entre corchetes junto al nombre del torrent
        emoji: Emoji a usar para cada torrent
    
    Returns:
        str: Mensaje formateado con torrents agrupados por tracker
    """
    from collections import defaultdict
    
    # Agrupar torrents por tracker
    trackers_dict = defaultdict(list)
    for torrent in torrents_con_tracker:
        nombre, tracker = torrent[0], torrent[1]
        detalle = torrent[2] if len(torrent) > 2 else None
        trackers_dict[tracker].append(f"{nombre} [{detalle}]" if detalle else nombre)
    
    # Construir mensaje agrupado
    message_parts = []
    for tracker, nombres in sorted(trackers_dict.items()):
        tracker_section = f"\n\n<b>Tracker:</b> {tracker}\n<b>Torrents:</b>"
        for nombre in nombres:
            tracker_section += f"\n\n{emoji} {nombre}"
        message_parts.append(tracker_section)
    
    return "".join(message_parts)
