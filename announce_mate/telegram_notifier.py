import aiohttp
import asyncio
from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SEND_TELEGRAM_ALERTS
from .logger import logger
from .database import DatabaseHandler

class TelegramNotifier:
    """Sends Telegram alerts for price-sensitive announcements."""

    def __init__(self, db: DatabaseHandler):
        self.db = db
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.session = None

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def send_message(self, text: str):
        if not SEND_TELEGRAM_ALERTS:
            return  # Skip sending if disabled
        await self._ensure_session()
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
        try:
            async with self.session.post(url, data=payload) as resp:
                if resp.status != 200:
                    logger.error(f"Telegram API failed with status {resp.status}")
                else:
                    logger.info(f"Telegram message sent: {text[:50]}...")
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")

    async def send_price_sensitive_alert(self, symbol: str, url: str, last_price=None, volume=None):
        msg = f"📢 <b>Price-sensitive Announcement</b>\n"
        msg += f"Symbol: {symbol}\n"
        if last_price is not None:
            msg += f"Last Price: {last_price}\n"
        if volume is not None:
            msg += f"Volume: {volume}\n"
        msg += f"URL: {url}"
        await self.send_message(msg)

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Telegram session closed.")
