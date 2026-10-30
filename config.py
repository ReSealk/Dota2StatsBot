import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="configs.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
E621_API = os.getenv("E621_API")
E621_LOGIN = os.getenv("E621_LOGIN")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

PREFIX = "d!"
USER_AGENT = "discordBot/2.0 (by Re_Sea1k)"

OPENDOTA = "https://api.opendota.com/api"
E621 = "https://e621.net"
STEAM_MEDIA = "https://media.steampowered.com"

ITEM_ICON_SIZE = 64
ITEM_ICON_PADDING = 8
LABEL_LINE_HEIGHT = 14
LABEL_MAX_LINES = 2
LABEL_BLOCK_HEIGHT = LABEL_LINE_HEIGHT * LABEL_MAX_LINES

# TTL кэша в секундах
CACHE_TTL_HEROES = 3600
CACHE_TTL_ITEMS = 3600
CACHE_TTL_MATCH = 30