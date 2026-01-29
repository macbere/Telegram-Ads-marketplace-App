"""
bot.py - Telegram Bot for Ads Marketplace
This bot handles interactions with channel owners and advertisers
"""

import asyncio
import logging
import os
import sys
import time
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError, TelegramNetworkError
from bot_handlers import setup_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get bot token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN or BOT_TOKEN == "placeholder-token":
    logger.error("❌ BOT_TOKEN not found or is placeholder!")
    logger.info("⚠️  Bot will not start, but API server should still work")
    sys.exit(1)

logger.info(f"✅ Bot token loaded: {BOT_TOKEN[:15]}...{BOT_TOKEN[-8:]}")


async def verify_bot_token(bot: Bot, max_retries=3):
    """
    Verify bot token with retries
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"🔍 Verifying bot token (attempt {attempt}/{max_retries})...")
            bot_info = await bot.get_me()
            logger.info(f"✅ Bot verified: @{bot_info.username} ({bot_info.first_name})")
            return True
        except TelegramUnauthorizedError as e:
            logger.error(f"❌ Unauthorized error: {e}")
            logger.error("The BOT_TOKEN is invalid or has been revoked!")
            return False
        except TelegramNetworkError as e:
            logger.warning(f"⚠️  Network error on attempt {attempt}: {e}")
            if attempt < max_retries:
                wait_time = attempt * 2
                logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("❌ Max retries reached. Network issues persist.")
                return False
        except Exception as e:
            logger.error(f"❌ Unexpected error verifying token: {e}")
            return False
    
    return False


async def main():
    """
    Main function to start the bot
    """
    logger.info("🚀 Starting Telegram Ads Marketplace Bot...")
    
    # Initialize bot
    try:
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher()
        logger.info("✅ Bot and Dispatcher initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize bot: {e}")
        sys.exit(1)
    
    # Verify bot token with retries
    if not await verify_bot_token(bot):
        logger.error("❌ Bot verification failed. Exiting.")
        await bot.session.close()
        sys.exit(1)
    
    # Setup all command and message handlers
    try:
        setup_handlers(dp)
        logger.info("✅ Command handlers registered")
    except Exception as e:
        logger.error(f"❌ Failed to setup handlers: {e}")
        await bot.session.close()
        sys.exit(1)
    
    # Start polling for updates
    try:
        logger.info("🎧 Starting polling for updates...")
        logger.info("✅ Bot is now running and ready to receive messages!")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("⏹️  Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Polling error: {e}")
    finally:
        await bot.session.close()
        logger.info("👋 Bot session closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)
