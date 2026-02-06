"""
Bot initialization and management - SIMPLIFIED VERSION
"""

import logging
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

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


async def set_bot_commands():
    """Set bot commands menu"""
    commands = [
        BotCommand(command="start", description="🏠 Main Menu"),
        BotCommand(command="help", description="❓ Help & Instructions"),
        BotCommand(command="stats", description="📊 Marketplace Statistics"),
    ]
    
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("✅ Bot commands menu set")
    except Exception as e:
        logger.error(f"❌ Failed to set commands: {e}")


async def start_bot():
    """Start the bot - SIMPLE VERSION"""
    logger.info("=" * 60)
    logger.info("🤖 BOT STARTING...")
    logger.info("=" * 60)
    
    try:
        # Delete any webhook
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted")
        
        # Verify bot
        me = await bot.get_me()
        logger.info(f"✅ Bot: @{me.username} (ID: {me.id})")
        
        # Set commands
        await set_bot_commands()
        
        # Setup handlers
        bot_handlers.setup_handlers(dp)
        logger.info("✅ Handlers registered")
        
        # Start polling
        logger.info("🎧 Starting polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Bot failed: {e}")
        raise


async def stop_bot():
    """Stop the bot"""
    logger.info("🛑 Stopping bot...")
    await dp.stop_polling()
    await bot.session.close()
    logger.info("✅ Bot stopped")
