import time
import random
import re
import html
from urllib.parse import urlparse, parse_qs, unquote
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pathlib import Path
from typing import Set, Optional
from .logger import logger

class VCodeManager:
    """Manages v-codes for API auth; caches with file timestamp."""

    def __init__(self, v_file: Path, cache_file: Path, cache_hours: int = 24):
        self.v_file = v_file
        self.cache_file = cache_file
        self.cache_hours = cache_hours
        self.seen_v: Set[str] = self._load_seen_v()
        self.last_fetch: float = self._load_cache_timestamp()

    def _load_seen_v(self) -> Set[str]:
        if not self.v_file.exists():
            return set()
        with open(self.v_file, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())

    def _save_v(self, new_v: Set[str]):
        with open(self.v_file, "a", encoding="utf-8") as f:
            for v in new_v:
                if v not in self.seen_v:
                    f.write(f"{v}\n")
                    self.seen_v.add(v)

    def _load_cache_timestamp(self) -> float:
        if not self.cache_file.exists():
            return 0
        with open(self.cache_file, "r") as f:
            val = f.read().strip()
        try:
            return float(val)
        except ValueError:
            return 0

    def _save_cache_timestamp(self):
        with open(self.cache_file, "w") as f:
            f.write(str(time.time()))
        self.last_fetch = time.time()

    def _extract_v(self, url: str) -> Optional[str]:
        u = html.unescape(unquote(url))
        parsed = urlparse(u)
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
        m = re.search(r"[?&]v=([^&'#]+)", u)
        return m.group(1) if m else None

    def _setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def _fetch_v_codes(self) -> Set[str]:
        logger.info("Fetching v-codes via Selenium.")
        driver = None
        try:
            driver = self._setup_driver()
            driver.get("https://www.asx.com.au/markets/trade-our-cash-market/announcements")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(5)
            last_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            page_html = driver.page_source
            found_v = set()
            cdn_regex = re.compile(r"https?://cdn-api\.markitdigital\.com/.*?/file/[^\"'\s>]+", re.IGNORECASE)
            for match in cdn_regex.finditer(page_html):
                vval = self._extract_v(match.group(0))
                if vval:
                    found_v.add(vval)

            logger.info(f"Extracted {len(found_v)} v-codes.")
            return found_v
        except Exception as e:
            logger.error(f"Selenium v-code fetch failed: {e}")
            return set()
        finally:
            if driver:
                driver.quit()

    def get_v(self, force_refresh: bool = False) -> str:
        now = time.time()
        if force_refresh or not self.seen_v or (now - self.last_fetch) > (self.cache_hours * 3600):
            new_v = self._fetch_v_codes()
            if new_v:
                self._save_v(new_v)
                self._save_cache_timestamp()
            elif not self.seen_v:
                raise RuntimeError("No v-codes available. Fix ChromeDriver.")
            else:
                logger.warning("Using cached v-codes; refresh failed.")
                self._save_cache_timestamp()

        return random.choice(list(self.seen_v))
