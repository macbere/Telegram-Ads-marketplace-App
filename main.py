"""
main.py - Combined FastAPI + Telegram Bot
Running in SINGLE PROCESS to prevent conflicts
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Global bot instance
bot_instance = None
dp = None
polling_task = None


async def start_bot():
    """Start the Telegram bot in background"""
    global bot_instance, dp, polling_task
    
    try:
        logger.info("🤖 Starting Telegram bot...")
        
        # Delete webhook if exists
        temp_bot = Bot(token=BOT_TOKEN)
        webhook_info = await temp_bot.get_webhook_info()
        if webhook_info.url:
            logger.info(f"🧹 Deleting webhook: {webhook_info.url}")
            await temp_bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(2)
        await temp_bot.session.close()
        
        # Create bot and dispatcher
        bot_instance = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        setup_handlers(dp)
        
        # Verify bot
        me = await bot_instance.get_me()
        logger.info(f"✅ Bot started: @{me.username}")
        
        # Start polling in background
        polling_task = asyncio.create_task(
            dp.start_polling(bot_instance, allowed_updates=dp.resolve_used_update_types())
        )
        
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")


async def stop_bot():
    """Stop the Telegram bot"""
    global bot_instance, polling_task
    
    logger.info("🛑 Stopping bot...")
    
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    if bot_instance:
        await bot_instance.session.close()
    
    logger.info("✅ Bot stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Application starting...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created")
    
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
    return {
        "status": "running",
        "message": "Telegram Ads Marketplace API is live! 🚀",
        "bot_status": "running" if bot_instance else "stopped",
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
    
    return {
        "status": "healthy",
        "database": db_status,
        "bot": "running" if bot_instance else "stopped",
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
    # Check if exists
    existing = db.query(Channel).filter(
        Channel.telegram_channel_id == channel_data.telegram_channel_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Channel already registered")
    
    # Get or create owner
    owner = db.query(User).filter(User.telegram_id == channel_data.owner_telegram_id).first()
    if not owner:
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
    
    return {
        "id": new_channel.id,
        "channel_title": new_channel.channel_title,
        "status": "created",
        "message": "Channel successfully registered!"
    }


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
    uvicorn.run("main:app", host="0.0.0.0", port=port)
