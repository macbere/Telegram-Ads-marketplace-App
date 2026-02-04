"""
Bot initialization and management
"""

import logging
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Import handlers
import bot_handlers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get bot token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

# Initialize bot and dispatcher
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher(storage=MemoryStorage())

# Global flag for polling task
_polling_task = None


async def start_bot():
    """Start the bot with polling"""
    global _polling_task
    
    logger.info("============================================================")
    logger.info("🤖 TELEGRAM BOT STARTUP SEQUENCE")
    logger.info("============================================================")
    
    # Step 1: Clean up any existing webhooks
    logger.info("STEP 1: Aggressive Webhook Cleanup")
    logger.info("🔥 AGGRESSIVE WEBHOOK CLEANUP")
    
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Attempt {attempt}/{max_attempts}: Checking webhook...")
            
            webhook_info = await bot.get_webhook_info()
            
            if webhook_info.url:
                logger.info(f"⚠️ Webhook found: {webhook_info.url}")
                logger.info("🧹 Deleting webhook...")
            else:
                logger.info("✅ No webhook found")
            
            # Force delete webhook regardless
            logger.info("🧹 Deleting webhook (forced)...")
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook confirmed deleted")
            
            # Wait for Telegram to release connection
            logger.info("⏳ Final 10-second wait for Telegram to release connection...")
            await asyncio.sleep(10)
            
            logger.info("✅ Cleanup complete")
            break
            
        except Exception as e:
            logger.error(f"❌ Cleanup attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                wait_time = 2 ** attempt
                logger.info(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("❌ All cleanup attempts failed, proceeding anyway...")
    
    # Step 2: Verify bot connection
    logger.info("STEP 2: Connection Verification")
    try:
        me = await bot.get_me()
        logger.info(f"✅ Bot verified: @{me.username} (ID: {me.id})")
    except Exception as e:
        logger.error(f"❌ Failed to verify bot: {e}")
        raise
    
    # Step 3: Register handlers
    logger.info("STEP 3: Bot Initialization")
    bot_handlers.setup_handlers(dp)
    logger.info("✅ Bot and dispatcher initialized")
    
    # Step 4: Start polling
    logger.info("STEP 4: Starting Polling")
    logger.info("🎧 Bot is now listening for messages...")
    logger.info("============================================================")
    
    # Start polling in background
    _polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))


async def stop_bot():
    """Stop the bot"""
    global _polling_task
    
    logger.info("🛑 Stopping bot...")
    
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
    
    await dp.stop_polling()
    await bot.session.close()
    
    logger.info("✅ Bot stopped")
