# test_bot.py
import os
import asyncio
from aiogram import Bot
from aiogram.enums import ParseMode

async def test_bot():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        print("❌ No BOT_TOKEN")
        return
    
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
    
    try:
        # Test 1: Can we connect to Telegram?
        me = await bot.get_me()
        print(f"✅ Bot connected: @{me.username} (ID: {me.id})")
        
        # Test 2: Delete webhook
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook deleted")
        
        # Test 3: Set commands
        from aiogram.types import BotCommand, BotCommandScopeDefault
        commands = [
            BotCommand(command="start", description="🏠 Main Menu"),
            BotCommand(command="help", description="❓ Help"),
            BotCommand(command="stats", description="📊 Stats"),
        ]
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        print("✅ Commands set")
        
        await bot.session.close()
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bot())
