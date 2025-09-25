from pathlib import Path
import random
from fake_useragent import UserAgent

# Paths
DATA_FOLDER = Path("data")
DATA_FOLDER.mkdir(exist_ok=True, parents=True)
DB_FILE = DATA_FOLDER / "asx_combined_data.db"
V_FILE = DATA_FOLDER / "asx_secret_codes.txt"
V_CACHE_FILE = DATA_FOLDER / "v_cache_timestamp.txt"

# API Endpoints
ANNOUNCEMENTS_URL = "https://asx.api.markitdigital.com/asx-research/1.0/markets/announcements"
API_BASE_URL = "https://asx.api.markitdigital.com/asx-research/1.0/companies"

# User Agents
USER_AGENTS_BASE = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]
USER_AGENTS = USER_AGENTS_BASE + [UserAgent().random for _ in range(10)]

HEADERS_POOL = [{
    "User-Agent": ua,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": random.choice(["en-US,en;q=0.9", "en-AU,en;q=0.8", "en-GB,en;q=0.7"]),
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.asx.com.au/markets/trade-our-cash-market/announcements",
    "Sec-Ch-Ua": '"Chromium";v="91", " Not;A Brand";v="99"',
    "Upgrade-Insecure-Requests": "1",
} for ua in USER_AGENTS]

# Proxy settings
USE_PROXIES = False
PROXIES = ["http://proxy1.example.com:8080", "http://proxy2.example.com:8080"] if USE_PROXIES else []

# Request & loop settings
REQUEST_DELAY_MIN = 5.0
REQUEST_DELAY_MAX = 15.0
BURST_LIMIT = 10
LOOP_INTERVAL = 300
MAX_CONCURRENT_REQUESTS = 3
API_TIMEOUT = 15
FAILURE_PAUSE = 600
V_CACHE_HOURS = 24

PRICE_SENSITIVE = False


# Telegram bot
SEND_TELEGRAM_ALERTS = True 
TELEGRAM_BOT_TOKEN = "8224872054:AAFv-lNYwO2K4PY7JjTGZC8HWeB4S8j-nbo"
TELEGRAM_CHAT_ID = "5821473557"  # e.g., "@yourchannel" or chat_id as integer
