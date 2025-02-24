import telebot
import time
from utils import setup_logger
from check_torrents_client_config import get_qbittorrent_client
from config import *

# Inicializa el bot con el token
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

logger = setup_logger(__name__)

def get_torrent_stats():

    client = get_qbittorrent_client()

    logger.info("Obteniendo estadísticas de torrents")
    
    stats = {
        'paused': [],
        'not_working': [],
        'updating': [],
        'working': [],
        'not_connect': []
    }
    
    for torrent in client.torrents_info():
        logger.debug(f"Procesando torrent: {torrent.name}")
        
        if torrent.state in ['pausedUP', 'pausedDL', 'stoppedUP', 'stoppedDL', 'error', 'unknown']:
            stats['paused'].append(torrent)
            logger.debug(f"Torrent en pausa: {torrent.name}")
            
        trackers = client.torrents_trackers(torrent.hash)
        for tracker in trackers:
            if tracker['status'] == 4:
                stats['not_working'].append(torrent)
                logger.debug(f"Torrent con tracker not working: {torrent.name}")
                break
            elif tracker['status'] == 3:
                stats['updating'].append(torrent)
                logger.debug(f"Torrent con tracker updating: {torrent.name}")
                break
            elif tracker['status'] == 2:
                stats['working'].append(torrent)
                logger.debug(f"Torrent con tracker working: {torrent.name}")
                break
            elif tracker['status'] == 1:
                stats['not_connect'].append(torrent)
                logger.debug(f"Torrent con tracker not connect: {torrent.name}")
                break
    
    logger.info(f"Procesados {sum(len(l) for l in stats.values())} torrents en total")
    return stats

def go_torrents_qbittorrent():
    logger.info("Iniciando proceso de torrents en qBittorrent")
    torrent_stats = get_torrent_stats()
    
    if PAUSADO > 0:
        paused_count = len(torrent_stats['paused'])
        logger.debug(f"Encontrados {paused_count} torrents pausados")
        
        if paused_count >= PAUSADO:
            message = f'<b>Hay {paused_count} torrents en pausa, parados o con error.</b>'
            if NOMBRE:
                for torrent in torrent_stats['paused']:
                    logger.debug(f"Torrent pausado: {torrent.name}")
                torrent_names = '\n\n🟠 '.join(torrent.name for torrent in torrent_stats['paused'])
                message += f'\n\n🟠 {torrent_names}.'
            send_telegram_message(message)
            logger.info(f"Enviada notificación de {paused_count} torrents pausados")

    if NO_TRACKER > 0:
        not_working_count = len(torrent_stats['not_working'])
        logger.debug(f"Encontrados {not_working_count} torrents con trackers not working")
        
        if not_working_count >= NO_TRACKER:
            message = f'<b>Hay {not_working_count} torrents con trackers "Not working".</b>'
            if NOMBRE:
                for torrent in torrent_stats['not_working']:
                    logger.debug(f"Torrent con tracker not working: {torrent.name}")
                torrent_names = '\n\n🔴 '.join(torrent.name for torrent in torrent_stats['not_working'])
                message += f'\n\n🔴 {torrent_names}.'
            send_telegram_message(message)
            logger.info(f"Enviada notificación de {not_working_count} torrents con trackers not working")

    if RESUMEN and (PAUSADO > 0 or NO_TRACKER > 0):
        logger.info("Generando resumen de estado")
        generar_resumen(torrent_stats)

def generar_resumen(stats):
    logger.debug("Preparando mensaje de resumen")
    message = f'<b>📝 Resumen qBittorrent</b>'    
    message_paused = f'Hay {len(stats["paused"])} torrents en pausa, parados o con error'
    message_updating = f'Hay {len(stats["updating"])} torrents con trackers "Updating"'
    message_working = f'Hay {len(stats["working"])} torrents con trackers "Working"'
    message_not_connect = f'Hay {len(stats["not_connect"])} torrents con trackers "Not connect"'
    message_not_working = f'Hay {len(stats["not_working"])} torrents con trackers "Not working"'
    
    message_resumen = (f'{message}\n'
                      f'🟠 {message_paused}\n'
                      f'🟡 {message_updating}\n'
                      f'🟢 {message_working}\n'
                      f'🔵 {message_not_connect}\n'
                      f'🔴 {message_not_working}')
    
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
    lines = message.split('\n')
    
    for line in lines:
        if len(current_part) + len(line) + 1 <= max_length:
            current_part += line + '\n'
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = line + '\n'
    
    if current_part:
        parts.append(current_part.strip())
    
    return parts

# Función para enviar mensajes a Telegram
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
