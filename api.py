import aiohttp
import asyncio
import random
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .config import HEADERS_POOL, PROXIES, MAX_CONCURRENT_REQUESTS, API_TIMEOUT, BURST_LIMIT, FAILURE_PAUSE
from .logger import logger
from typing import Optional, Dict

class APISession:
    """Async session with headers rotation and optional proxies."""

    def __init__(self):
        timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
        self.session = aiohttp.ClientSession(timeout=timeout)
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self.header_index = 0
        self.request_count = 0
        self.minute_start = time.time()

    def _rotate_header(self):
        self.header_index = (self.header_index + 1) % len(HEADERS_POOL)
        return HEADERS_POOL[self.header_index]

    def _select_proxy(self):
        return random.choice(PROXIES) if PROXIES else None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30),
           retry=retry_if_exception_type(aiohttp.ClientError))
    async def get_json(self, url: str) -> Optional[Dict]:
        now = time.time()
        if now - self.minute_start > 60:
            self.request_count = 0
            self.minute_start = now
        if self.request_count >= BURST_LIMIT:
            await asyncio.sleep(random.uniform(20, 40))
        self.request_count += 1

        headers = self._rotate_header()
        proxy = self._select_proxy()
        async with self.semaphore:
            try:
                logger.debug(f"Requesting: {url}")
                async with self.session.get(url, headers=headers, proxy=proxy) as resp:
                    resp.raise_for_status()
                    resp_text = await resp.text()
                    if resp.status == 429 or "rate limit" in resp_text.lower():
                        logger.warning(f"Rate limited: {url}")
                        await asyncio.sleep(FAILURE_PAUSE)
                        raise aiohttp.ClientError("Rate limited")
                    return await resp.json()
            except aiohttp.ClientError as e:
                logger.error(f"API failed: {e}")
                raise

    async def close(self):
        await self.session.close()
        logger.info("API session closed.")
