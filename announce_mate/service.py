import asyncio
from .config import (
    ANNOUNCEMENTS_URL, DB_FILE, V_FILE, V_CACHE_FILE,
    MAX_CONCURRENT_REQUESTS, LOOP_INTERVAL, SEND_TELEGRAM_ALERTS
)
from .database import DatabaseHandler
from .vcode import VCodeManager
from .api import APISession
from .fetcher import MarketDataFetcher
from .display import display_announcements
from .telegram_notifier import TelegramNotifier
from .logger import logger


class AnnouncementService:
    def __init__(self):
        self.db = DatabaseHandler(DB_FILE)
        self.v_manager = VCodeManager(V_FILE, V_CACHE_FILE)
        self.api_session = APISession()
        self.fetcher = MarketDataFetcher(self.api_session)
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self.telegram_bot = TelegramNotifier(self.db) if SEND_TELEGRAM_ALERTS else None
        self._running = True

    async def run(self):
        while self._running:
            try:
                await self.process_announcements()
            except Exception as e:
                logger.error(f"Unexpected error in loop: {e}")
            await self.wait_with_countdown()

    async def process_announcements(self):
        try:
            v_code = self.v_manager.get_v(force_refresh=False)
        except Exception as e:
            logger.warning(f"V-code refresh failed: {e}")
            return

        try:
            data = await self.api_session.get_json(ANNOUNCEMENTS_URL)
        except Exception as e:
            logger.error(f"Announcement fetch failed: {e}")
            return

        if not data:
            logger.info("No data received from API.")
            return

        items = data.get("data", {}).get("items", [])
        logger.info(f"Fetched {len(items)} announcements.")

        for item in items:
            item["url"] = (
                f"https://cdn-api.markitdigital.com/apiman-gateway/ASX/"
                f"asx-research/1.0/file/{item['documentKey']}?v={v_code}"
            )

        new_announcements = self.db.save_announcements(items)
        if not new_announcements:
            logger.info("No new announcements to process.")
            return

        display_announcements(new_announcements)

        await asyncio.gather(*(self.fetch_and_notify(a) for a in new_announcements if a.get("symbol")))

    async def fetch_and_notify(self, announcement):
        symbol = announcement["symbol"]
        async with self.semaphore:
            try:
                data = await asyncio.wait_for(self.fetcher.fetch_all_for_symbol(symbol), timeout=30)
                if data:
                    self.db.save_company_data(data["combined"])
                    self.db.save_volumes(symbol, data["volumes"])
                    if self.telegram_bot:
                        await self.telegram_bot.handle_announcement(announcement, data["combined"])
                else:
                    logger.warning(f"No market data for {symbol}")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching data for {symbol}, skipping...")
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")

    async def wait_with_countdown(self, msg="Next check in"):
        for i in range(LOOP_INTERVAL, 0, -1):
            print(f"{msg} {i} seconds...", end="\r")
            await asyncio.sleep(1)
        print(" " * 50, end="\r")

    async def close(self):
        await self.api_session.close()
        self.db.close()
