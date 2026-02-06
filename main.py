"""
main.py - FastAPI server for Telegram Ads Marketplace
Complete with Purchase Flow, Payment, and Order Management
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, get_db, Base
from models import User, Channel, Deal, Post, ChannelStats, Order
from pydantic import BaseModel
from typing import Optional, Dict
import os
from datetime import datetime
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import bot setup
import bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Application starting...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created/verified")
    
    # Start bot in background
    import asyncio
    bot_task = asyncio.create_task(bot.start_bot())
    
    yield
    
    # Shutdown
    await bot.stop_bot()
    if not bot_task.done():
        bot_task.cancel()
    logger.info("👋 Application stopped")


# Initialize FastAPI app
app = FastAPI(
    title="Telegram Ads Marketplace API",
    description="Complete marketplace with purchase flow and order management",
    version="2.0.0",
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
    channel_title: str
    channel_username: Optional[str] = None
    pricing: Dict[str, float]


class OrderCreate(BaseModel):
    buyer_telegram_id: int
    channel_id: int
    ad_type: str
    price: float


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    payment_method: Optional[str] = None
    payment_transaction_id: Optional[str] = None
    creative_content: Optional[str] = None
    creative_media_id: Optional[str] = None
    post_url: Optional[str] = None
    paid_at: Optional[str] = None
    completed_at: Optional[str] = None


# ============================================================================
# HEALTH CHECK & INFO ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Telegram Ads Marketplace API v2.0 - With Purchase Flow! 🚀",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "features": ["browse", "purchase", "payment", "orders", "creative_submission"]
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
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get marketplace statistics"""
    try:
        total_users = db.query(User).count()
        total_channels = db.query(Channel).count()
        total_deals = db.query(Deal).count()
        total_orders = db.query(Order).count()
        active_orders = db.query(Order).filter(
            Order.status.in_(["paid", "processing"])
        ).count()
        
        return {
            "total_users": total_users,
            "total_channels": total_channels,
            "total_deals": total_deals,
            "total_orders": total_orders,
            "active_orders": active_orders,
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
        return {
            "id": existing_user.id,
            "telegram_id": existing_user.telegram_id,
            "username": existing_user.username,
            "first_name": existing_user.first_name,
            "is_channel_owner": existing_user.is_channel_owner,
            "is_advertiser": existing_user.is_advertiser,
            "created_at": existing_user.created_at.isoformat()
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
        "is_advertiser": new_user.is_advertiser,
        "created_at": new_user.created_at.isoformat()
    }


@app.get("/users/{telegram_id}")
async def get_user(telegram_id: int, db: Session = Depends(get_db)):
    """Get user by Telegram ID"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "is_channel_owner": user.is_channel_owner,
        "is_advertiser": user.is_advertiser,
        "created_at": user.created_at.isoformat()
    }


# ============================================================================
# CHANNEL ENDPOINTS
# ============================================================================

@app.get("/channels/")
async def list_channels(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List all active channels"""
    channels = db.query(Channel).filter(
        Channel.status == "active"
    ).offset(skip).limit(limit).all()
    
    result = []
    for channel in channels:
        result.append({
            "id": channel.id,
            "channel_title": channel.channel_title,
            "channel_username": channel.channel_username,
            "subscribers": channel.subscribers,
            "avg_views": channel.avg_views,
            "pricing": channel.pricing,
            "status": channel.status,
            "created_at": channel.created_at.isoformat()
        })
    
    return result


@app.get("/channels/{channel_id}")
async def get_channel(channel_id: int, db: Session = Depends(get_db)):
    """Get channel details"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    return {
        "id": channel.id,
        "channel_title": channel.channel_title,
        "channel_username": channel.channel_username,
        "subscribers": channel.subscribers,
        "avg_views": channel.avg_views,
        "pricing": channel.pricing,
        "status": channel.status,
        "created_at": channel.created_at.isoformat()
    }


@app.post("/channels/")
async def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    """Create a new channel listing"""
    # Check if channel already exists
    existing = db.query(Channel).filter(
        Channel.telegram_channel_id == channel.telegram_channel_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Channel already exists")
    
    # Get or create user
    user = db.query(User).filter(User.telegram_id == channel.owner_telegram_id).first()
    if not user:
        user = User(telegram_id=channel.owner_telegram_id, is_channel_owner=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.is_channel_owner = True
        db.commit()
    
    # Create channel
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
        "status": new_channel.status,
        "created_at": new_channel.created_at.isoformat()
    }


# ============================================================================
# ORDER ENDPOINTS (NEW)
# ============================================================================

@app.post("/orders/")
async def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Create a new order"""
    # Verify channel exists
    channel = db.query(Channel).filter(Channel.id == order.channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Get or create buyer
    buyer = db.query(User).filter(User.telegram_id == order.buyer_telegram_id).first()
    if not buyer:
        buyer = User(telegram_id=order.buyer_telegram_id, is_advertiser=True)
        db.add(buyer)
        db.commit()
        db.refresh(buyer)
    else:
        buyer.is_advertiser = True
        db.commit()
    
    # Create order
    new_order = Order(
        buyer_id=buyer.id,
        channel_id=order.channel_id,
        ad_type=order.ad_type,
        price=order.price,
        status="pending_payment"
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    logger.info(f"✅ Order created: #{new_order.id}")
    
    return {
        "id": new_order.id,
        "buyer_id": new_order.buyer_id,
        "channel_id": new_order.channel_id,
        "ad_type": new_order.ad_type,
        "price": new_order.price,
        "status": new_order.status,
        "created_at": new_order.created_at.isoformat()
    }


@app.get("/orders/user/{telegram_id}")
async def get_user_orders(telegram_id: int, db: Session = Depends(get_db)):
    """Get all orders for a user"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return []
    
    orders = db.query(Order).filter(Order.buyer_id == user.id).order_by(Order.created_at.desc()).all()
    
    result = []
    for order in orders:
        result.append({
            "id": order.id,
            "channel_id": order.channel_id,
            "ad_type": order.ad_type,
            "price": order.price,
            "status": order.status,
            "payment_method": order.payment_method,
            "created_at": order.created_at.isoformat(),
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "completed_at": order.completed_at.isoformat() if order.completed_at else None
        })
    
    return result


@app.get("/orders/{order_id}")
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get order details"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "id": order.id,
        "buyer_id": order.buyer_id,
        "channel_id": order.channel_id,
        "ad_type": order.ad_type,
        "price": order.price,
        "status": order.status,
        "payment_method": order.payment_method,
        "payment_transaction_id": order.payment_transaction_id,
        "creative_content": order.creative_content,
        "creative_media_id": order.creative_media_id,
        "post_url": order.post_url,
        "created_at": order.created_at.isoformat(),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None
    }


@app.patch("/orders/{order_id}")
async def update_order(order_id: int, update: OrderUpdate, db: Session = Depends(get_db)):
    """Update order details"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update fields
    if update.status is not None:
        order.status = update.status
    
    if update.payment_method is not None:
        order.payment_method = update.payment_method
    
    if update.payment_transaction_id is not None:
        order.payment_transaction_id = update.payment_transaction_id
    
    if update.creative_content is not None:
        order.creative_content = update.creative_content
    
    if update.creative_media_id is not None:
        order.creative_media_id = update.creative_media_id
    
    if update.post_url is not None:
        order.post_url = update.post_url
    
    if update.paid_at is not None:
        order.paid_at = datetime.fromisoformat(update.paid_at.replace('Z', '+00:00'))
    
    if update.completed_at is not None:
        order.completed_at = datetime.fromisoformat(update.completed_at.replace('Z', '+00:00'))
    
    db.commit()
    db.refresh(order)
    
    logger.info(f"✅ Order updated: #{order_id}, status={order.status}")
    
    return {
        "id": order.id,
        "status": order.status,
        "payment_method": order.payment_method,
        "payment_transaction_id": order.payment_transaction_id,
        "updated": True
    }


# ============================================================================
# DEAL ENDPOINTS (Legacy - kept for compatibility)
# ============================================================================

@app.get("/deals/")
async def list_deals(user_id: int = None, status: str = None, db: Session = Depends(get_db)):
    """List deals"""
    query = db.query(Deal)
    
    if user_id:
        query = query.filter(Deal.advertiser_id == user_id)
    
    if status:
        query = query.filter(Deal.status == status)
    
    deals = query.all()
    
    result = []
    for deal in deals:
        result.append({
            "id": deal.id,
            "advertiser_id": deal.advertiser_id,
            "channel_id": deal.channel_id,
            "ad_type": deal.ad_type,
            "price": deal.price,
            "status": deal.status,
            "created_at": deal.created_at.isoformat()
        })
    
    return result


@app.get("/deals/{deal_id}")
async def get_deal(deal_id: int, db: Session = Depends(get_db)):
    """Get deal details"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return {
        "id": deal.id,
        "advertiser_id": deal.advertiser_id,
        "channel_id": deal.channel_id,
        "ad_type": deal.ad_type,
        "price": deal.price,
        "status": deal.status,
        "creative_content": deal.creative_content,
        "creative_media_id": deal.creative_media_id,
        "post_url": deal.post_url,
        "created_at": deal.created_at.isoformat(),
        "completed_at": deal.completed_at.isoformat() if deal.completed_at else None
    }


# ============================================================================
# RUN SERVER - FIXED FOR RENDER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    
    # CRITICAL FOR RENDER: Must bind to 0.0.0.0
    logger.info(f"🚀 Starting server on port {port}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # MUST BE 0.0.0.0 for Render
        port=port,
        reload=False  # Disable reload in production
    )
