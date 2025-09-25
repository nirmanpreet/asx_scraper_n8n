import html
from xml.etree.ElementTree import fromstring
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .api import APISession
from .config import API_BASE_URL
from .logger import logger
import asyncio

class MarketDataFetcher:
    """Fetches market data asynchronously with robust error handling."""

    def __init__(self, api_session: APISession, max_retries: int = 3, retry_delay: float = 2.0):
        self.api_session = api_session
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def _fetch_json_safe(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch JSON with retry and exception handling."""
        for attempt in range(1, self.max_retries + 1):
            try:
                data = await self.api_session.get_json(url)
                if data and isinstance(data, dict):
                    return data
                logger.warning(f"Invalid or empty data from {url} (attempt {attempt})")
            except Exception as e:
                logger.error(f"Error fetching {url} (attempt {attempt}): {e}")
            await asyncio.sleep(self.retry_delay)
        logger.error(f"Failed to fetch data from {url} after {self.max_retries} attempts")
        return None

    async def _fetch_header(self, ticker: str) -> Optional[Dict[str, Any]]:
        url = f"{API_BASE_URL}/{ticker}/header"
        data = await self._fetch_json_safe(url)
        if data and (header := data.get("data")):
            try:
                return {
                    "symbol": header.get("symbol"),
                    "priceLast": header.get("priceLast"),
                    "priceChange": header.get("priceChange"),
                    "volume": header.get("volume"),
                    "marketCap": header.get("marketCap"),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                logger.error(f"Error parsing header for {ticker}: {e}")
        return None

    async def _fetch_key_stats(self, ticker: str) -> Optional[Dict[str, Any]]:
        url = f"{API_BASE_URL}/{ticker}/key-statistics"
        data = await self._fetch_json_safe(url)
        if data and (stats := data.get("data")):
            try:
                income_statements = stats.get("incomeStatement", [])
                latest_income = income_statements[0] if income_statements else {}
                return {
                    "volumeAverage": stats.get("volumeAverage"),
                    "numOfShares": stats.get("numOfShares"),
                    "netIncome": latest_income.get("netIncome")
                }
            except Exception as e:
                logger.error(f"Error parsing key stats for {ticker}: {e}")
        return None

    async def _fetch_volumes(self, ticker: str) -> List[Dict[str, str]]:
        url = f"{API_BASE_URL}/{ticker}/key-statistics-charts?height=270&width=250"
        data = await self._fetch_json_safe(url)
        if not data or not (svg_str := data.get("data", {}).get("fiveTradingVolume")):
            return []

        svg_unescaped = html.unescape(svg_str)
        try:
            root = fromstring(svg_unescaped)
        except Exception as e:
            logger.error(f"Failed to parse SVG for {ticker}: {e}")
            return []

        date_map, volume_map = {}, {}
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        for text in root.findall('.//svg:text', ns):
            try:
                x, y, content = text.get('x'), text.get('y'), text.text or ""
                if x and y:
                    y_val = int(float(y))
                    if 240 <= y_val <= 260:
                        date_map.setdefault(x, {})['day' if y_val < 250 else 'month'] = content.strip()
                if x and re.match(r'^[\d,.]+[MK]$', content):
                    volume_map[x] = content
            except Exception as e:
                logger.warning(f"Error processing SVG text element: {e}")

        results = []
        for dx, d in date_map.items():
            if 'day' in d and 'month' in d:
                try:
                    dx_val = float(dx)
                    closest_x = min(volume_map.keys(), key=lambda vx: abs(float(vx) - dx_val), default=None)
                    if closest_x:
                        results.append({"date": f"{d['day']} {d['month']}", "volume": volume_map[closest_x]})
                except Exception as e:
                    logger.warning(f"Error mapping date to volume for {ticker}: {e}")
        return results

    async def fetch_all_for_symbol(self, ticker: str) -> Dict[str, Any]:
        """Fetch combined market data and volumes with partial results allowed."""
        result: Dict[str, Any] = {}
        volumes: List[Dict[str, str]] = []

        try:
            header = await self._fetch_header(ticker)
            if header:
                result.update(header)
            else:
                logger.warning(f"No header data for {ticker}")

            stats = await self._fetch_key_stats(ticker)
            if stats:
                result.update(stats)
            else:
                logger.warning(f"No key stats data for {ticker}")

            volumes = await self._fetch_volumes(ticker)
            if not volumes:
                logger.warning(f"No volumes data for {ticker}")

            if result or volumes:
                return {"combined": result, "volumes": volumes}
            else:
                logger.error(f"No usable data for {ticker}")
                return {}

        except Exception as e:
            logger.error(f"Unexpected error fetching data for {ticker}: {e}")
            return {}
