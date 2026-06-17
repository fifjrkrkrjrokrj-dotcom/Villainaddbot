import os
import logging
import asyncio
import nest_asyncio
from telethon import TelegramClient
import config
import database
import handlers
import userbot_manager

# Create directories if they do not exist
os.makedirs("logs", exist_ok=True)
os.makedirs(config.USER_DATA_DIR, exist_ok=True)

# Configure logging to console and a log file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/userbot_manager.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Apply Windows compatibility patch for nested asyncio loops
nest_asyncio.apply()

async def main():
    logger.info("Initializing database connection...")
    database.db_init()
    
    # Initialize Bot Client
    logger.info("Initializing Bot client...")
    bot = TelegramClient("bot_session", config.API_ID, config.API_HASH)
    
    # Register all command and callback handlers
    logger.info("Registering event handlers...")
    handlers.register_all_handlers(bot)
    
    logger.info("Starting bot manager...")
    await bot.start(bot_token=config.BOT_TOKEN)
    logger.info("Telegram Bot Manager is running successfully.")
    
    # Resume userbots that were running prior to shutdown in background
    asyncio.create_task(userbot_manager.start_all_running_bots())
    
    # Start Gmail autopay approval check loop in background
    from handlers.payments_extended import start_gmail_polling
    asyncio.create_task(start_gmail_polling(bot))
    
    try:
        # Run main bot until connection is lost
        await bot.run_until_disconnected()
    finally:
        # Stop all background userbots gracefully
        await userbot_manager.stop_all_bots()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot Manager stopped gracefully.")
