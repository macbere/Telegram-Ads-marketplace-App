"""
bot.py - Telegram Bot for Ads Marketplace (Webhook Mode)
This bot handles interactions using webhooks instead of polling
"""

import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot_handlers import setup_handlers
from fastapi import Request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get bot token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found!")
    raise ValueError("BOT_TOKEN is required")

logger.info(f"✅ Bot token loaded: {BOT_TOKEN[:15]}...{BOT_TOKEN[-8:]}")

# Initialize bot and dispatcher (singleton pattern)
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Setup handlers once
setup_handlers(dp)
logger.info("✅ Bot handlers registered")


async def setup_webhook():
    """
    Setup webhook for the bot
    """
    if not WEBHOOK_URL:
        logger.warning("⚠️  WEBHOOK_URL not set - bot will not receive updates")
        return False
    
    try:
        webhook_info = await bot.get_webhook_info()
        
        if webhook_info.url != WEBHOOK_URL:
            logger.info(f"🔧 Setting webhook to: {WEBHOOK_URL}")
            await bot.set_webhook(
                url=WEBHOOK_URL,
                drop_pending_updates=True  # Clear any pending updates
            )
            logger.info("✅ Webhook set successfully")
        else:
            logger.info(f"✅ Webhook already configured: {WEBHOOK_URL}")
        
        # Verify bot
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot verified: @{bot_info.username} ({bot_info.first_name})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to setup webhook: {e}")
        return False


async def process_update(request: Request):
    """
    Process incoming webhook update from Telegram
    """
    try:
        update_data = await request.json()
        from aiogram.types import Update
        update = Update(**update_data)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"❌ Error processing update: {e}")
        return {"ok": False, "error": str(e)}


async def remove_webhook():
    """
    Remove webhook (cleanup)
    """
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🗑️  Webhook removed")
    except Exception as e:
        logger.error(f"❌ Error removing webhook: {e}")
