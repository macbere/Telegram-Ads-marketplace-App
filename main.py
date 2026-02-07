"""
main.py - FastAPI server
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, get_db, Base
from models import User, Channel, Order
from pydantic import BaseModel
from typing import Optional, Dict
import os
from datetime import datetime
from contextlib import asynccontextmanager
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    logger.info("🚀 Starting application...")
    
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database ready")
    
    bot_task = asyncio.create_task(bot.start_bot())
    
    yield
    
    logger.info("👋 Shutting down...")
    await bot.stop_bot()
    if not bot_task.done():
        bot_task.cancel()
    logger.info("✅ Application stopped")


app = FastAPI(title="Telegram Ads Marketplace", version="1.0", lifespan=lifespan)


class ChannelCreate(BaseModel):
    owner_telegram_id: int
    telegram_channel_id: int
    channel_title: str
    channel_username: Optional[str] = None
    pricing: Dict[str, float]


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "running",
        "service": "Telegram Ads Marketplace",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check with DB"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "healthy", "database": f"error: {str(e)}"}


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get stats"""
    try:
        users = db.query(User).count()
        channels = db.query(Channel).count()
        orders = db.query(Order).count()
        
        return {
            "total_users": users,
            "total_channels": channels,
            "total_orders": orders,
            "active_orders": 0
        }
    except:
        return {
            "total_users": 0,
            "total_channels": 0,
            "total_orders": 0,
            "active_orders": 0
        }


@app.post("/users/")
async def create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create or get user"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        return {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "is_channel_owner": user.is_channel_owner,
            "is_advertiser": user.is_advertiser
        }
    
    new_user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "telegram_id": new_user.telegram_id,
        "username": new_user.username,
        "first_name": new_user.first_name,
        "is_channel_owner": new_user.is_channel_owner,
        "is_advertiser": new_user.is_advertiser
    }


@app.get("/users/{telegram_id}")
async def get_user(telegram_id: int, db: Session = Depends(get_db)):
    """Get user"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "is_channel_owner": user.is_channel_owner,
        "is_advertiser": user.is_advertiser
    }


@app.post("/channels/")
async def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    """Create channel"""
    existing = db.query(Channel).filter(
        Channel.telegram_channel_id == channel.telegram_channel_id
    ).first()
    
    if existing:
        raise HTTPException(400, "Channel already exists")
    
    user = db.query(User).filter(User.telegram_id == channel.owner_telegram_id).first()
    if not user:
        user = User(telegram_id=channel.owner_telegram_id, is_channel_owner=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.is_channel_owner = True
        db.commit()
    
    new_channel = Channel(
        owner_id=user.id,
        telegram_channel_id=channel.telegram_channel_id,
        channel_title=channel.channel_title,
        channel_username=channel.channel_username,
        pricing=channel.pricing
    )
    
    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)
    
    return {
        "id": new_channel.id,
        "channel_title": new_channel.channel_title,
        "channel_username": new_channel.channel_username,
        "pricing": new_channel.pricing,
        "status": new_channel.status
    }


@app.get("/channels/")
async def list_channels(db: Session = Depends(get_db)):
    """List channels"""
    channels = db.query(Channel).filter(Channel.status == "active").limit(20).all()
    
    result = []
    for channel in channels:
        result.append({
            "id": channel.id,
            "channel_title": channel.channel_title,
            "channel_username": channel.channel_username,
            "subscribers": channel.subscribers,
            "avg_views": channel.avg_views,
            "pricing": channel.pricing,
            "status": channel.status
        })
    
    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
