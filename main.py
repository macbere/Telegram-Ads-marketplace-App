"""
main.py - FastAPI server for Telegram Ads Marketplace
NOW WITH CHANNEL CREATION ENDPOINT!
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
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(
    title="Telegram Ads Marketplace API",
    description="MVP for connecting channel owners and advertisers",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup
@app.on_event("startup")
async def startup():
    """Create database tables on startup"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")


# ============================================================================
# PYDANTIC MODELS FOR REQUEST VALIDATION
# ============================================================================

class ChannelCreate(BaseModel):
    owner_telegram_id: int
    telegram_channel_id: int
    channel_username: Optional[str] = None
    channel_title: str
    pricing: Dict[str, float]
    status: str = "active"


# ============================================================================
# HEALTH CHECK & INFO ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Telegram Ads Marketplace API is live! 🚀",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Detailed health check - tests database connection"""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get overall marketplace statistics"""
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
    """Create or get a user by Telegram ID"""
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
    """Get detailed information about a specific channel"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@app.post("/channels/create")
async def create_channel(channel_data: ChannelCreate, db: Session = Depends(get_db)):
    """
    🔥 NEW! Create a new channel listing
    Called by the bot when channel owner registers their channel
    """
    # Check if channel already exists
    existing = db.query(Channel).filter(
        Channel.telegram_channel_id == channel_data.telegram_channel_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Channel already registered")
    
    # Get or create owner user
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
        subscribers=0,  # Will be updated by stats fetcher
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
    """Get detailed information about a specific deal"""
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
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
