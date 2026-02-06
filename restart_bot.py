"""
Emergency bot restart - fixes ALL conflicts
"""

import os
import asyncio
import logging
from aiogram import Bot
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def nuclear_restart():
    """Nuclear option - completely reset bot connection"""
    
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        logger.error("❌ No BOT_TOKEN")
        return
    
    bot = Bot(token=BOT_TOKEN)
    
    logger.info("💣 NUCLEAR RESTART INITIATED")
    
    # Step 1: Delete webhook 10 times
    for i in range(10):
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info(f"✅ Webhook deleted attempt {i+1}")
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"❌ Attempt {i+1}: {e}")
    
    # Step 2: Set empty commands
    try:
        await bot.set_my_commands([])
        logger.info("✅ Commands cleared")
    except Exception as e:
        logger.error(f"❌ Clear commands: {e}")
    
    # Step 3: Close session
    await bot.session.close()
    logger.info("✅ Session closed")
    
    logger.info("✅ Nuclear restart complete!")
    logger.info("⚠️ Wait 30 seconds before starting main.py")

if __name__ == "__main__":
    asyncio.run(nuclear_restart())
