"""
bot.py - Telegram Bot for Ads Marketplace
Polling mode with forced webhook removal and proper shutdown handling
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

logger.info(f"✅ Token loaded: {BOT_TOKEN[:15]}...{BOT_TOKEN[-8:]}")

# Global bot instance for cleanup
bot_instance = None


async def force_delete_webhook():
    """Force delete webhook before starting polling - ROBUST VERSION"""
    temp_bot = Bot(token=BOT_TOKEN)
    try:
        logger.info("🔍 Checking webhook status...")
        webhook_info = await temp_bot.get_webhook_info()
        
        if webhook_info.url:
            logger.warning(f"⚠️  Active webhook detected: {webhook_info.url}")
            logger.info("🧹 Deleting webhook with drop_pending_updates=True...")
            
            result = await temp_bot.delete_webhook(drop_pending_updates=True)
            
            if result:
                logger.info("✅ Webhook deleted successfully")
                await asyncio.sleep(3)  # Give Telegram time to process
                
                # Verify deletion
                verify_info = await temp_bot.get_webhook_info()
                if verify_info.url:
                    logger.error(f"❌ Webhook still active after deletion: {verify_info.url}")
                    raise Exception("Webhook deletion failed")
                else:
                    logger.info("✅ Webhook deletion verified")
            else:
                logger.error("❌ Webhook deletion returned False")
                raise Exception("Webhook deletion failed")
        else:
            logger.info("✅ No active webhook - ready for polling")
            
    except Exception as e:
        logger.error(f"❌ Error during webhook check/deletion: {e}")
        raise
    finally:
        await temp_bot.session.close()


async def main():
    """Start the bot with polling"""
    global bot_instance
    
    try:
        # STEP 1: Force delete any existing webhook
        logger.info("=" * 50)
        logger.info("STEP 1: Webhook Cleanup")
        logger.info("=" * 50)
        await force_delete_webhook()
        
        # STEP 2: Initialize fresh bot instance
        logger.info("=" * 50)
        logger.info("STEP 2: Bot Initialization")
        logger.info("=" * 50)
        bot_instance = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher()
        
        # STEP 3: Verify bot works
        logger.info("=" * 50)
        logger.info("STEP 3: Bot Verification")
        logger.info("=" * 50)
        me = await bot_instance.get_me()
        logger.info(f"✅ Bot verified: @{me.username} (ID: {me.id})")
        
        # STEP 4: Setup handlers
        logger.info("=" * 50)
        logger.info("STEP 4: Handler Registration")
        logger.info("=" * 50)
        setup_handlers(dp)
        logger.info("✅ All handlers registered")
        
        # STEP 5: Start polling
        logger.info("=" * 50)
        logger.info("STEP 5: Starting Polling Mode")
        logger.info("=" * 50)
        logger.info("🎧 Bot is now LISTENING for messages...")
        logger.info("💬 Try sending /start to the bot!")
        logger.info("=" * 50)
        
        await dp.start_polling(
            bot_instance,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True  # Drop old updates
        )
        
    except KeyboardInterrupt:
        logger.info("⏹️  Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Fatal error in main loop: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        if bot_instance:
            logger.info("🧹 Cleaning up bot session...")
            await bot_instance.session.close()
            logger.info("✅ Bot session closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Application crashed: {e}", exc_info=True)
        sys.exit(1)
