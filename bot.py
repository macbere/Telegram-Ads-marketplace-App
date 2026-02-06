"""
Bot initialization and management - WITH PERSISTENT MENU
"""

import logging
import os
import asyncio
import time
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

# Global flag for polling task
_polling_task = None


async def set_bot_commands():
    """Set bot commands menu (the menu button in Telegram)"""
    commands = [
        BotCommand(command="start", description="🏠 Main Menu"),
        BotCommand(command="help", description="❓ Help & Instructions"),
        BotCommand(command="stats", description="📊 Marketplace Statistics"),
    ]
    
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    logger.info("✅ Bot commands menu set")


async def aggressive_webhook_cleanup():
    """AGGRESSIVE cleanup of any webhooks"""
    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"🧹 Attempt {attempt}/{max_attempts}: Cleaning webhooks...")
            
            # Delete webhook aggressively
            await bot.delete_webhook(drop_pending_updates=True)
            
            # Wait and check
            await asyncio.sleep(3)
            
            webhook_info = await bot.get_webhook_info()
            if not webhook_info.url:
                logger.info("✅ Webhook cleanup successful")
                return True
            
            logger.warning(f"⚠️ Webhook still exists: {webhook_info.url}")
            
            if attempt < max_attempts:
                wait_time = 5 * attempt
                logger.info(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
                
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
            if attempt < max_attempts:
                await asyncio.sleep(5)
    
    logger.error("❌ Failed to cleanup webhooks after all attempts")
    return False


async def force_stop_other_instances():
    """Try to stop other bot instances"""
    logger.info("🛑 Attempting to stop other bot instances...")
    
    try:
        # This tells Telegram to stop sending updates to old connections
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Close any existing sessions
        if hasattr(bot, 'session') and not bot.session.closed:
            await bot.session.close()
            logger.info("✅ Closed existing bot session")
        
        # Wait for connections to close
        await asyncio.sleep(5)
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to stop instances: {e}")
        return False


async def start_bot():
    """Start the bot with polling - ULTRA AGGRESSIVE CLEANUP"""
    global _polling_task
    
    logger.info("=" * 60)
    logger.info("🤖 TELEGRAM BOT STARTUP SEQUENCE")
    logger.info("=" * 60)
    
    # STEP 0: Force stop any other instances
    logger.info("STEP 0: Nuclear Cleanup")
    await force_stop_other_instances()
    
    # STEP 1: Aggressive webhook cleanup
    logger.info("STEP 1: Aggressive Webhook Cleanup")
    cleanup_success = await aggressive_webhook_cleanup()
    
    if not cleanup_success:
        logger.warning("⚠️ Proceeding despite cleanup failure")
    
    # STEP 2: Extra long wait for Telegram
    logger.info("STEP 2: Final Wait (15 seconds)")
    await asyncio.sleep(15)
    
    # STEP 3: Verify bot connection
    logger.info("STEP 3: Connection Verification")
    try:
        me = await bot.get_me()
        logger.info(f"✅ Bot verified: @{me.username} (ID: {me.id})")
    except Exception as e:
        logger.error(f"❌ Failed to verify bot: {e}")
        raise
    
    # STEP 4: Set bot commands menu
    logger.info("STEP 4: Setting Bot Commands Menu")
    try:
        await set_bot_commands()
    except Exception as e:
        logger.error(f"⚠️ Failed to set commands: {e}")
        # Non-critical, continue
    
    # STEP 5: Register handlers
    logger.info("STEP 5: Bot Initialization")
    bot_handlers.setup_handlers(dp)
    logger.info("✅ Bot and dispatcher initialized")
    
    # STEP 6: Start polling with aggressive settings
    logger.info("STEP 6: Starting Polling")
    logger.info("🎧 Bot is now listening for messages...")
    logger.info("=" * 60)
    
    # Start polling with specific settings to avoid conflicts
    _polling_task = asyncio.create_task(
        dp.start_polling(
            bot, 
            handle_signals=False,
            allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"],
            drop_pending_updates=True
        )
    )


async def stop_bot():
    """Stop the bot"""
    global _polling_task
    
    logger.info("🛑 Stopping bot...")
    
    try:
        # Stop polling
        if _polling_task:
            _polling_task.cancel()
            try:
                await _polling_task
            except asyncio.CancelledError:
                logger.info("✅ Polling task cancelled")
            except Exception as e:
                logger.error(f"❌ Error cancelling task: {e}")
        
        # Close dispatcher
        await dp.stop_polling()
        logger.info("✅ Dispatcher stopped")
        
        # Delete webhook to free connection
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook deleted")
        except Exception as e:
            logger.error(f"⚠️ Error deleting webhook: {e}")
        
        # Close bot session
        await bot.session.close()
        logger.info("✅ Bot session closed")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")
    
    logger.info("✅ Bot stopped completely")
