"""
main.py - Combined FastAPI + Telegram Bot
FINAL VERSION - All issues resolved
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, get_db, Base
from models import User, Channel, Deal, Post, ChannelStats
from pydantic import BaseModel
from typing import Optional, Dict
import os
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager

# Bot imports
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot_handlers import setup_handlers

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN environment variable not set!")
    raise ValueError("BOT_TOKEN is required")

# Global bot instance
bot_instance = None
dp = None
polling_task = None


async def wait_for_telegram_release():
    """Wait for Telegram to release any existing polling connections"""
    logger.info("⏳ Waiting for Telegram to release any existing connections...")
    await asyncio.sleep(5)
    logger.info("✅ Wait complete")


async def cleanup_webhook():
    """Force delete webhook and wait for Telegram to process"""
    temp_bot = Bot(token=BOT_TOKEN)
    try:
        logger.info("🔍 Checking for existing webhook...")
        webhook_info = await temp_bot.get_webhook_info()
        
        if webhook_info.url:
            logger.warning(f"⚠️  Found active webhook: {webhook_info.url}")
            logger.info("🧹 Deleting webhook...")
            
            result = await temp_bot.delete_webhook(drop_pending_updates=True)
            
            if result:
                logger.info("✅ Webhook deleted successfully")
                logger.info("⏳ Waiting 10 seconds for Telegram to process...")
                await asyncio.sleep(10)
            else:
                logger.error("❌ Webhook deletion failed")
                raise Exception("Failed to delete webhook")
        else:
            logger.info("✅ No webhook found")
            # Still wait to ensure clean start
            await wait_for_telegram_release()
            
    except Exception as e:
        logger.error(f"❌ Error during webhook cleanup: {e}")
        # Wait anyway to be safe
        await wait_for_telegram_release()
    finally:
        await temp_bot.session.close()


async def verify_bot_connection():
    """Verify bot can connect before starting polling"""
    temp_bot = Bot(token=BOT_TOKEN)
    try:
        me = await temp_bot.get_me()
        logger.info(f"✅ Bot verified: @{me.username} (ID: {me.id})")
        return True
    except Exception as e:
        logger.error(f"❌ Bot verification failed: {e}")
        return False
    finally:
        await temp_bot.session.close()


async def start_bot():
    """Start the Telegram bot with proper error handling"""
    global bot_instance, dp, polling_task
    
    try:
        logger.info("=" * 60)
        logger.info("🤖 TELEGRAM BOT STARTUP SEQUENCE")
        logger.info("=" * 60)
        
        # Step 1: Cleanup webhook
        logger.info("STEP 1: Webhook Cleanup")
        await cleanup_webhook()
        
        # Step 2: Verify connection
        logger.info("STEP 2: Connection Verification")
        if not await verify_bot_connection():
            raise Exception("Bot verification failed")
        
        # Step 3: Initialize bot
        logger.info("STEP 3: Bot Initialization")
        bot_instance = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher()
        setup_handlers(dp)
        logger.info("✅ Bot and dispatcher initialized")
        
        # Step 4: Start polling with retry mechanism
        logger.info("STEP 4: Starting Polling")
        logger.info("🎧 Bot is now listening for messages...")
        logger.info("=" * 60)
        
        polling_task = asyncio.create_task(
            dp.start_polling(
                bot_instance,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=True  # Drop old messages
            )
        )
        
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}", exc_info=True)
        if bot_instance:
            await bot_instance.session.close()


async def stop_bot():
    """Stop the Telegram bot gracefully"""
    global bot_instance, polling_task
    
    logger.info("🛑 Stopping bot...")
    
    # Cancel polling
    if polling_task and not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            logger.info("✅ Polling cancelled")
    
    # Cleanup webhook and close session
    if bot_instance:
        try:
            logger.info("🧹 Deleting webhook before shutdown...")
            await bot_instance.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(2)
            logger.info("✅ Webhook deleted")
        except Exception as e:
            logger.warning(f"⚠️  Error deleting webhook: {e}")
        
        await bot_instance.session.close()
        logger.info("✅ Bot session closed")
    
    logger.info("✅ Bot stopped cleanly")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    # Startup
    logger.info("🚀 Application starting...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created/verified")
    
    # Start bot
    await start_bot()
    
    yield
    
    # Shutdown
    logger.info("🛑 Application shutting down...")
    await stop_bot()


# Initialize FastAPI app
app = FastAPI(
    title="Telegram Ads Marketplace API",
    description="MVP for connecting channel owners and advertisers",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChannelCreate(BaseModel):
    owner_telegram_id: int
    telegram_channel_id: int
    channel_username: Optional[str] = None
    channel_title: str
    pricing: Dict[str, float]
    status: str = "active"


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    bot_status = "running" if bot_instance and not polling_task.done() else "stopped"
    return {
        "status": "running",
        "message": "Telegram Ads Marketplace API is live! 🚀",
        "bot_status": bot_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Detailed health check"""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    bot_status = "running" if bot_instance and polling_task and not polling_task.done() else "stopped"
    
    return {
        "status": "healthy",
        "database": db_status,
        "bot": bot_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get marketplace statistics"""
    try:
        total_users = db.query(User).count()
        total_channels = db.query(Channel).count()
        total_deals = db.query(Deal).count()
        active_deals = db.query(Deal).filter(
            Deal.status.in_(["pending", "accepted", "creative_submitted", "creative_approved", "posted"])
        ).count()
        
        return {
            "total_users": total_users,
            "total_channels": total_channels,
            "total_deals": total_deals,
            "active_deals": active_deals,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ============================================================================
# USER ENDPOINTS
# ============================================================================

@app.post("/users/")
async def create_user(
    telegram_id: int,
    username: str = None,
    first_name: str = None,
    db: Session = Depends(get_db)
):
    """Create or get a user"""
    try:
        existing_user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if existing_user:
            return existing_user
        
        new_user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{telegram_id}")
async def get_user(telegram_id: int, db: Session = Depends(get_db)):
    """Get user by Telegram ID"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ============================================================================
# CHANNEL ENDPOINTS
# ============================================================================

@app.get("/channels/")
async def list_channels(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List all active channels"""
    channels = db.query(Channel).filter(
        Channel.status == "active"
    ).offset(skip).limit(limit).all()
    return channels


@app.get("/channels/{channel_id}")
async def get_channel(channel_id: int, db: Session = Depends(get_db)):
    """Get channel details"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@app.post("/channels/create")
async def create_channel(channel_data: ChannelCreate, db: Session = Depends(get_db)):
    """Create a new channel listing"""
    try:
        logger.info(f"📝 Creating channel: {channel_data.channel_title}")
        
        # Check if exists
        existing = db.query(Channel).filter(
            Channel.telegram_channel_id == channel_data.telegram_channel_id
        ).first()
        
        if existing:
            logger.warning(f"⚠️  Channel already exists: {channel_data.channel_title}")
            raise HTTPException(status_code=400, detail="Channel already registered")
        
        # Get or create owner
        owner = db.query(User).filter(User.telegram_id == channel_data.owner_telegram_id).first()
        if not owner:
            logger.info(f"Creating new user for channel owner: {channel_data.owner_telegram_id}")
            owner = User(telegram_id=channel_data.owner_telegram_id)
            db.add(owner)
            db.commit()
            db.refresh(owner)
        
        # Create channel
        new_channel = Channel(
            owner_id=owner.id,
            telegram_channel_id=channel_data.telegram_channel_id,
            channel_username=channel_data.channel_username,
            channel_title=channel_data.channel_title,
            pricing=channel_data.pricing,
            status=channel_data.status,
            subscribers=0,
            avg_views=0,
            avg_reach=0
        )
        
        db.add(new_channel)
        db.commit()
        db.refresh(new_channel)
        
        logger.info(f"✅ Channel created successfully: ID {new_channel.id}")
        
        return {
            "id": new_channel.id,
            "channel_title": new_channel.channel_title,
            "status": "created",
            "message": "Channel successfully registered!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ============================================================================
# DEAL ENDPOINTS
# ============================================================================

@app.get("/deals/")
async def list_deals(
    user_id: int = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """List deals"""
    query = db.query(Deal)
    
    if user_id:
        query = query.filter(Deal.advertiser_id == user_id)
    
    if status:
        query = query.filter(Deal.status == status)
    
    deals = query.all()
    return deals


@app.get("/deals/{deal_id}")
async def get_deal(deal_id: int, db: Session = Depends(get_db)):
    """Get deal details"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
