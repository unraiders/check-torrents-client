from check_torrents_qbittorrent import go_torrents_qbittorrent
from check_torrents_synology_ds import go_torrents_synology_ds
from check_torrents_transmission import go_torrents_transmission
from config import TORRENT_CLIENT, VERSION
from utils import setup_logger

VERSION="2.3.0"

# Initialize logger
logger = setup_logger("pausar_torrents")

if __name__ == "__main__":
    torrent_client = TORRENT_CLIENT

    if torrent_client == "qbittorrent":
        go_torrents_qbittorrent()
    elif torrent_client == "transmission":
        go_torrents_transmission()
    elif torrent_client == "synology_ds":
        go_torrents_synology_ds()
    else:
        raise ValueError(f"Cliente de torrent no soportado: {torrent_client}")
