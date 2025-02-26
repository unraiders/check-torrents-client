import os

from dotenv import load_dotenv

load_dotenv()

TORRENT_CLIENT = os.getenv("TORRENT_CLIENT").lower()

TORRENT_CLIENT_HOST = os.getenv("TORRENT_CLIENT_HOST")
TORRENT_CLIENT_PORT = os.getenv("TORRENT_CLIENT_PORT")
TORRENT_CLIENT_USER = os.getenv("TORRENT_CLIENT_USER")
TORRENT_CLIENT_PASSWORD = os.getenv("TORRENT_CLIENT_PASSWORD")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PAUSADO = int(os.getenv("PAUSADO", 1))
NO_TRACKER = int(os.getenv("NO_TRACKER", 1))

NOMBRE = os.getenv("NOMBRE", "0") == "1"
RESUMEN = os.getenv("RESUMEN", "0") == "1"

DEBUG = os.getenv("DEBUG", "0") == "1"

TZ = os.getenv("TZ", "Europe/Madrid")
