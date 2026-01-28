"""
main.py - FastAPI server for Telegram Ads Marketplace
This is the main application entry point
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, get_db, Base
from models import User, Channel, Deal, Post, ChannelStats
import os
from datetime import datetime

# Create all database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Telegram Ads Marketplace API",
    description="MVP for connecting channel owners and advertisers",
    version="1.0.0"
)

# Enable CORS (Cross-Origin Resource Sharing) for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH CHECK & INFO ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """
    Health check endpoint - confirms the server is running
    """
    return {
        "status": "running",
        "message": "Telegram Ads Marketplace API is live! 🚀",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Detailed health check - tests database connection
    """
    try:
        # Try to query the database (SQLAlchemy 2.0 syntax)
        from sqlalchemy import text
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
    """
    Get overall marketplace statistics
    """
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
async def create_user(telegram_id: int, username: str = None, first_name: str = None, db: Session = Depends(get_db)):
    """
    Create or get a user by Telegram ID
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if existing_user:
        return existing_user
    
    # Create new user
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
    """
    Get user by Telegram ID
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ============================================================================
# CHANNEL ENDPOINTS
# ============================================================================

@app.get("/channels/")
async def list_channels(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    List all active channels (for advertisers to browse)
    """
    channels = db.query(Channel).filter(
        Channel.status == "active"
    ).offset(skip).limit(limit).all()
    return channels


@app.get("/channels/{channel_id}")
async def get_channel(channel_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific channel
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


# ============================================================================
# DEAL ENDPOINTS
# ============================================================================

@app.get("/deals/")
async def list_deals(user_id: int = None, status: str = None, db: Session = Depends(get_db)):
    """
    List deals, optionally filtered by user or status
    """
    query = db.query(Deal)
    
    if user_id:
        query = query.filter(Deal.advertiser_id == user_id)
    
    if status:
        query = query.filter(Deal.status == status)
    
    deals = query.all()
    return deals


@app.get("/deals/{deal_id}")
async def get_deal(deal_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific deal
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


# ============================================================================
# WEBHOOK ENDPOINT (for Telegram bot)
# ============================================================================

@app.post("/webhook/{bot_token}")
async def telegram_webhook(bot_token: str):
    """
    Webhook endpoint for receiving Telegram updates
    This will be used by the Telegram bot to receive messages
    """
    expected_token = os.getenv("BOT_TOKEN", "")
    
    if bot_token != expected_token.split(":")[-1]:  # Simple token validation
        raise HTTPException(status_code=403, detail="Invalid bot token")
    
    return {"status": "ok"}


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
