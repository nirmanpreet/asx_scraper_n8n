import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Set

logger = logging.getLogger(__name__)

class DatabaseHandler:
    """Manages SQLite database: announcements, company data, volumes."""

    def __init__(self, db_file: Path):
        self.db_file = db_file
        logger.info(f"Initializing database at {db_file}")
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        """Create tables and indexes if they don't exist."""
        logger.info("Creating database schema.")
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS announcements (
                documentKey TEXT PRIMARY KEY,
                symbol TEXT,
                headline TEXT,
                date TEXT,
                url TEXT,
                isPriceSensitive INTEGER
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS company_data (
                symbol TEXT PRIMARY KEY,
                priceLast REAL,
                priceChange REAL,
                volume INTEGER,
                marketCap INTEGER,
                volumeAverage REAL,
                numOfShares INTEGER,
                netIncome REAL,
                last_updated TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS five_day_volume (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                date TEXT,
                volume TEXT,
                UNIQUE(symbol, date)
            )
        ''')
        # Indexes for faster querying
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_announcements_symbol ON announcements(symbol);')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_announcements_date ON announcements(date);')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_volumes_symbol ON five_day_volume(symbol);')
        self.conn.commit()
        logger.info("Database schema initialized.")

    def save_announcements(self, items: List[Dict]) -> List[Dict]:
        """
        Save announcements in batch.
        Returns only the announcements that were actually new (inserted).
        """
        logger.info(f"Saving {len(items)} announcements.")
        data_to_insert = [
            (
                item.get("documentKey"),
                item.get("symbol"),
                item.get("headline"),
                item.get("date"),
                item.get("url"),
                int(item.get("isPriceSensitive", False))
            ) for item in items
        ]

        new_items = []
        for item_tuple, item_dict in zip(data_to_insert, items):
            try:
                self.cursor.execute('''
                    INSERT OR IGNORE INTO announcements
                    (documentKey, symbol, headline, date, url, isPriceSensitive)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', item_tuple)
                if self.cursor.rowcount > 0:
                    # Only append announcements actually inserted
                    new_items.append(item_dict)
            except sqlite3.Error as e:
                logger.error(f"DB error inserting announcement {item_dict.get('documentKey')}: {e}")

        self.conn.commit()
        logger.info(f"Saved {len(new_items)} new announcements.")
        return new_items  # Return only new announcements

    def save_company_data(self, data: Dict):
        """Insert or update company market data."""
        logger.info(f"Saving market data for {data.get('symbol')}")
        try:
            self.cursor.execute('''
                INSERT INTO company_data (
                    symbol, priceLast, priceChange, volume, marketCap,
                    volumeAverage, numOfShares, netIncome, last_updated
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    priceLast=excluded.priceLast,
                    priceChange=excluded.priceChange,
                    volume=excluded.volume,
                    marketCap=excluded.marketCap,
                    volumeAverage=excluded.volumeAverage,
                    numOfShares=excluded.numOfShares,
                    netIncome=excluded.netIncome,
                    last_updated=excluded.last_updated
            ''', (
                data.get('symbol'),
                data.get('priceLast'),
                data.get('priceChange'),
                data.get('volume'),
                data.get('marketCap'),
                data.get('volumeAverage'),
                data.get('numOfShares'),
                data.get('netIncome'),
                data.get('last_updated')
            ))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"DB error saving company data: {e}")

    def save_volumes(self, symbol: str, volumes: List[Dict]):
        """Save last 5-day volumes for a symbol."""
        logger.info(f"Saving volumes for {symbol} (batched)")
        data_to_insert = [(symbol, v['date'], v['volume']) for v in volumes]
        self.cursor.executemany('''
            INSERT OR IGNORE INTO five_day_volume (symbol, date, volume)
            VALUES (?, ?, ?)
        ''', data_to_insert)
        self.conn.commit()

    def get_price_sensitive_symbols(
        self,
        items: List[Dict],
        ignore_strings: List[str] = ["Suspension and Removal"]
    ) -> Set[str]:
        """Return set of price-sensitive symbols ignoring specified headlines."""
        symbols = set()
        for item in items:
            if item.get("isPriceSensitive"):
                ignore = any(ign in item.get("headline", "") for ign in ignore_strings)
                if not ignore:
                    symbols.add(item["symbol"])
        return symbols

    def close(self):
        """Close the database connection."""
        self.conn.close()
        logger.info("Database closed.")
