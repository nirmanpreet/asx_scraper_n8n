import asyncio
from .service import AnnouncementService
from .logger import logger

async def main():
    logger.info("===== Starting AnnounceMate Scraper =====")
    service = AnnouncementService()
    try:
        await service.run()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown signal received. Closing scraper...")
    finally:
        await service.close()
        logger.info("Scraper stopped gracefully.")

if __name__ == "__main__":
    asyncio.run(main())
