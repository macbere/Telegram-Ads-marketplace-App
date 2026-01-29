"""
bot.py - Telegram Bot for Ads Marketplace
Runs in polling mode - simple and reliable
"""

import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot_handlers import setup_handlers

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN or len(BOT_TOKEN) < 20:
    logger.error("❌ Invalid BOT_TOKEN")
    sys.exit(1)

logger.info(f"✅ Token: {BOT_TOKEN[:15]}...{BOT_TOKEN[-8:]}")


async def main():
    """Start the bot with polling"""
    
    # Initialize
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Verify bot works
    try:
        me = await bot.get_me()
        logger.info(f"✅ Bot: @{me.username}")
    except Exception as e:
        logger.error(f"❌ Bot verification failed: {e}")
        await bot.session.close()
        sys.exit(1)
    
    # Remove any existing webhook (critical!)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook removed (using polling)")
    except Exception as e:
        logger.warning(f"⚠️  Could not remove webhook: {e}")
    
    # Setup handlers
    setup_handlers(dp)
    logger.info("✅ Handlers registered")
    
    # Start polling
    try:
        logger.info("🎧 Polling started - bot is ready!")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("⏹️  Stopped by user")
    except Exception as e:
        logger.error(f"❌ Polling error: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Fatal: {e}")
        sys.exit(1)
