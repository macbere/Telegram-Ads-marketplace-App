"""
Bot initialization
"""

import logging
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

import bot_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found")
    raise ValueError("BOT_TOKEN is required")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())

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
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted")
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot: @{bot_info.username} (ID: {bot_info.id})")
        await setup_bot()
        bot_handlers.setup_handlers(dp)
        logger.info("✅ Handlers registered")
        logger.info("🎧 Bot is now listening...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Bot failed to start: {e}")
        raise

async def stop_bot():
    logger.info("🛑 Stopping bot...")
    await dp.stop_polling()
    await bot.session.close()
    logger.info("✅ Bot stopped")
