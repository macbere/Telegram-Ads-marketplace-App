"""
Bot initialization
"""

import logging
import os
import asyncio
import time
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

import bot_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found")
    raise ValueError("BOT_TOKEN is required")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

async def aggressive_cleanup():
    """Aggressively clean up old bot instances"""
    logger.info("🧹 Aggressive cleanup started...")
    
    try:
        # Try multiple times to delete webhook
        for i in range(5):
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                logger.info(f"✅ Webhook deleted attempt {i+1}")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"⚠️ Attempt {i+1}: {e}")
        
        # Wait longer
        logger.info("⏳ Waiting 10 seconds for Telegram to release connection...")
        await asyncio.sleep(10)
        
        return True
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        return False

async def setup_bot():
    try:
        commands = [BotCommand(command="start", description="🏠 Main Menu"), BotCommand(command="help", description="❓ Help"), BotCommand(command="stats", description="📊 Stats")]
        await bot.set_my_commands(commands)
        logger.info("✅ Bot commands set")
    except Exception as e:
        logger.error(f"❌ Failed to set commands: {e}")

async def start_bot():
    logger.info("🤖 Starting Telegram bot...")
    
    try:
        # AGGRESSIVE CLEANUP FIRST
        await aggressive_cleanup()
        
        # Get bot info
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot: @{bot_info.username} (ID: {bot_info.id})")
        
        await setup_bot()
        
        bot_handlers.setup_handlers(dp)
        logger.info("✅ Handlers registered")
        
        logger.info("🎧 Bot is now listening...")
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
        
    except Exception as e:
        logger.error(f"❌ Bot failed to start: {e}")
        # Try one more time after delay
        logger.info("🔄 Retrying in 30 seconds...")
        await asyncio.sleep(30)
        await start_bot()

async def stop_bot():
    logger.info("🛑 Stopping bot...")
    await dp.stop_polling()
    await bot.session.close()
    logger.info("✅ Bot stopped")
