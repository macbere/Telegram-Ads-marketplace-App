"""
Bot initialization - SIMPLE & RELIABLE
"""

import logging
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

# Import handlers
import bot_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found in environment")
    raise ValueError("BOT_TOKEN is required")

# Create bot with new aiogram 3.7+ syntax
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)

# Create dispatcher
dp = Dispatcher(storage=MemoryStorage())


async def setup_bot():
    """Setup bot commands"""
    try:
        commands = [
            BotCommand(command="start", description="🏠 Main Menu"),
            BotCommand(command="help", description="❓ Help & Instructions"),
            BotCommand(command="stats", description="📊 Marketplace Stats"),
        ]
        await bot.set_my_commands(commands)
        logger.info("✅ Bot commands set")
    except Exception as e:
        logger.error(f"❌ Failed to set commands: {e}")


async def start_bot():
    """Start the bot"""
    logger.info("🤖 Starting Telegram bot...")
    
    try:
        # Delete any existing webhook
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted")
        
        # Get bot info
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot: @{bot_info.username} (ID: {bot_info.id})")
        
        # Setup commands
        await setup_bot()
        
        # Setup handlers
        bot_handlers.setup_handlers(dp)
        logger.info("✅ Handlers registered")
        
        # Start polling
        logger.info("🎧 Bot is now listening...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Bot failed to start: {e}")
        raise


async def stop_bot():
    """Stop the bot"""
    logger.info("🛑 Stopping bot...")
    await dp.stop_polling()
    await bot.session.close()
    logger.info("✅ Bot stopped")
