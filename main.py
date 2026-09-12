import asyncio
import logging
from bot.main import start_bot
from core.auto_scanner import start_scanner
from bot.main import bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

async def main():
    logger.info("Initializing Memecoin Sniper Bot...")
    
    # Start telegram bot (which also starts target sniper, auto-scanner is manual via bot)
    await start_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
