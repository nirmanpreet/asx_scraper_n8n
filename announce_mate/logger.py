import logging
from pathlib import Path

LOG_FOLDER = Path("logs")
LOG_FOLDER.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FOLDER / "asx_combined_scraper.log", mode="a")
    ]
)

logger = logging.getLogger("AnnounceMate")
