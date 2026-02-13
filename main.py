"""
FastAPI Backend with Database Integration - PHASE 1
Complete API endpoints for user and channel management
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, List
from pathlib import Path
import logging
import asyncio
import os

from database import engine, get_db, init_db
from models import Base, User, Channel, Order, ChannelStats
import bot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("🚀 Starting application...")
    
    # Initialize database
    logger.info("📊 Initializing database...")
    init_db()
    logger.info("✅ Database initialized")
    
    # Start bot
    bot_task = asyncio.create_task(bot.start_bot())
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down...")
    await bot.stop_bot()
    if not bot_task.done():
        bot_task.cancel()
    logger.info("✅ Application stopped")


app = FastAPI(
    title="Telegram Ads Marketplace API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Telegram Ads Marketplace API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/webapp", response_class=HTMLResponse)
async def serve_webapp():
    """Serve the beautiful Web App UI"""
    try:
        html_path = Path(__file__).parent / "index.html"
        if html_path.exists():
            return FileResponse(html_path)
        return HTMLResponse("<h1>Web App UI - Coming Soon</h1>")
    except Exception as e:
        logger.error(f"Error serving webapp: {e}")
        return HTMLResponse("<h1>Error loading Web App</h1>")


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Detailed health check"""
    try:
        # Test database connection (SQLAlchemy 2.0 syntax)
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================================
# USER ENDPOINTS
# ============================================================================

@app.post("/users/")
async def create_or_get_user(
    telegram_id: int,
    username: str = "",
    first_name: str = "",
    db: Session = Depends(get_db)
):
    """Create or get user by Telegram ID"""
    logger.info(f"📝 User request: telegram_id={telegram_id}")
    
    # Check if user exists
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if user:
        logger.info(f"✅ User exists: {user.id}")
        return {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "is_channel_owner": user.is_channel_owner,
            "is_advertiser": user.is_advertiser,
            "created_at": user.created_at.isoformat()
        }
    
    # Create new user
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"✅ User created: {user.id}")
    
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "is_channel_owner": user.is_channel_owner,
        "is_advertiser": user.is_advertiser,
        "created_at": user.created_at.isoformat()
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


@app.get("/users/telegram/{telegram_id}")
async def get_user_by_telegram(telegram_id: int, db: Session = Depends(get_db)):
    """Get user by Telegram ID (alternative endpoint)"""
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


@app.patch("/users/{telegram_id}")
async def update_user_role(
    telegram_id: int,
    update_data: dict,
    db: Session = Depends(get_db)
):
    """Update user roles"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update roles from JSON body
    if "is_channel_owner" in update_data:
        user.is_channel_owner = update_data["is_channel_owner"]
    
    if "is_advertiser" in update_data:
        user.is_advertiser = update_data["is_advertiser"]
    
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "is_channel_owner": user.is_channel_owner,
        "is_advertiser": user.is_advertiser
    }


# ============================================================================
# CHANNEL ENDPOINTS
# ============================================================================

@app.post("/channels/")
async def create_channel(
    channel_data: dict,
    db: Session = Depends(get_db)
):
    """Create a new channel listing"""
    owner_telegram_id = channel_data.get("owner_telegram_id")
    telegram_channel_id = channel_data.get("telegram_channel_id")
    channel_title = channel_data.get("channel_title")
    channel_username = channel_data.get("channel_username")
    pricing = channel_data.get("pricing", {})
    
    logger.info(f"📢 Channel creation: {channel_title} ({telegram_channel_id})")
    
    # Get or create owner
    owner = db.query(User).filter(User.telegram_id == owner_telegram_id).first()
    if not owner:
        owner = User(telegram_id=owner_telegram_id)
        db.add(owner)
        db.commit()
        db.refresh(owner)
    
    # Update owner role
    if not owner.is_channel_owner:
        owner.is_channel_owner = True
        db.commit()
    
    # Check if channel already exists
    existing = db.query(Channel).filter(
        Channel.telegram_channel_id == telegram_channel_id
    ).first()
    
    if existing:
        logger.info(f"⚠️ Channel already exists: {existing.id}")
        raise HTTPException(status_code=400, detail="Channel already exists")
    
    # Create channel
    channel = Channel(
        owner_id=owner.id,
        telegram_channel_id=telegram_channel_id,
        channel_title=channel_title,
        channel_username=channel_username,
        pricing=pricing
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    
    # Create channel stats
    stats = ChannelStats(channel_id=channel.id)
    db.add(stats)
    db.commit()
    
    logger.info(f"✅ Channel created: {channel.id}")
    
    return {
        "id": channel.id,
        "owner_id": channel.owner_id,
        "telegram_channel_id": channel.telegram_channel_id,
        "channel_title": channel.channel_title,
        "channel_username": channel.channel_username,
        "pricing": channel.pricing,
        "status": channel.status,
        "created_at": channel.created_at.isoformat()
    }


@app.get("/channels/")
async def list_channels(
    status: str = "active",
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List all active channels"""
    channels = db.query(Channel).filter(
        Channel.status == status
    ).limit(limit).all()
    
    result = []
    for channel in channels:
        result.append({
            "id": channel.id,
            "telegram_channel_id": channel.telegram_channel_id,
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
    """Get channel by ID"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    return {
        "id": channel.id,
        "owner_id": channel.owner_id,
        "telegram_channel_id": channel.telegram_channel_id,
        "channel_title": channel.channel_title,
        "channel_username": channel.channel_username,
        "subscribers": channel.subscribers,
        "avg_views": channel.avg_views,
        "pricing": channel.pricing,
        "status": channel.status,
        "created_at": channel.created_at.isoformat()
    }


@app.get("/channels/owner/{telegram_id}")
async def get_owner_channels(telegram_id: int, db: Session = Depends(get_db)):
    """Get all channels owned by a user"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        return []
    
    channels = db.query(Channel).filter(Channel.owner_id == user.id).all()
    
    result = []
    for channel in channels:
        result.append({
            "id": channel.id,
            "telegram_channel_id": channel.telegram_channel_id,
            "channel_title": channel.channel_title,
            "channel_username": channel.channel_username,
            "pricing": channel.pricing,
            "status": channel.status,
            "created_at": channel.created_at.isoformat()
        })
    
    return result


# ============================================================================
# ORDER ENDPOINTS
# ============================================================================

@app.post("/orders/")
async def create_order(
    order_data: dict,
    db: Session = Depends(get_db)
):
    """Create a new order"""
    buyer_telegram_id = order_data.get("buyer_telegram_id")
    channel_id = order_data.get("channel_id")
    ad_type = order_data.get("ad_type")
    price = order_data.get("price")
    
    logger.info(f"🛒 Order creation: channel={channel_id}, type={ad_type}")
    
    # Get or create buyer
    buyer = db.query(User).filter(User.telegram_id == buyer_telegram_id).first()
    if not buyer:
        buyer = User(telegram_id=buyer_telegram_id)
        db.add(buyer)
        db.commit()
        db.refresh(buyer)
    
    # Update buyer role
    if not buyer.is_advertiser:
        buyer.is_advertiser = True
        db.commit()
    
    # Verify channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Create order
    order = Order(
        buyer_id=buyer.id,
        channel_id=channel_id,
        ad_type=ad_type,
        price=price,
        status="pending_payment"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    logger.info(f"✅ Order created: {order.id}")
    
    return {
        "id": order.id,
        "buyer_id": order.buyer_id,
        "channel_id": order.channel_id,
        "ad_type": order.ad_type,
        "price": order.price,
        "status": order.status,
        "created_at": order.created_at.isoformat()
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
            "payment_transaction_id": order.payment_transaction_id,
            "creative_content": order.creative_content,
            "creative_media_id": order.creative_media_id,
            "post_url": order.post_url,
            "created_at": order.created_at.isoformat(),
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "completed_at": order.completed_at.isoformat() if order.completed_at else None
        })
    
    return result


@app.get("/orders/{order_id}")
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get single order by ID"""
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get buyer telegram_id
    buyer = db.query(User).filter(User.id == order.buyer_id).first()
    buyer_telegram_id = buyer.telegram_id if buyer else None
    
    return {
        "id": order.id,
        "buyer_id": order.buyer_id,
        "buyer_telegram_id": buyer_telegram_id,
        "channel_id": order.channel_id,
        "ad_type": order.ad_type,
        "price": order.price,
        "status": order.status,
        "payment_method": order.payment_method,
        "payment_transaction_id": order.payment_transaction_id,
        "creative_content": order.creative_content,
        "creative_media_id": order.creative_media_id,
        "post_url": order.post_url,
        "notes": order.notes,
        "created_at": order.created_at.isoformat(),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None
    }


@app.get("/orders/channel/{channel_id}")
async def get_channel_orders(channel_id: int, db: Session = Depends(get_db)):
    """Get all orders for a channel"""
    orders = db.query(Order).filter(Order.channel_id == channel_id).order_by(Order.created_at.desc()).all()
    
    result = []
    for order in orders:
        result.append({
            "id": order.id,
            "buyer_id": order.buyer_id,
            "ad_type": order.ad_type,
            "price": order.price,
            "status": order.status,
            "payment_transaction_id": order.payment_transaction_id,
            "creative_content": order.creative_content,
            "creative_media_id": order.creative_media_id,
            "post_url": order.post_url,
            "created_at": order.created_at.isoformat(),
            "completed_at": order.completed_at.isoformat() if order.completed_at else None
        })
    
    return result


@app.patch("/orders/{order_id}")
async def update_order(
    order_id: int,
    update_data: dict,
    db: Session = Depends(get_db)
):
    """Update order details"""
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update fields from JSON body
    if "status" in update_data:
        order.status = update_data["status"]
    if "payment_method" in update_data:
        order.payment_method = update_data["payment_method"]
    if "payment_transaction_id" in update_data:
        order.payment_transaction_id = update_data["payment_transaction_id"]
    if "creative_content" in update_data:
        order.creative_content = update_data["creative_content"]
    if "creative_media_id" in update_data:
        order.creative_media_id = update_data["creative_media_id"]
    if "post_url" in update_data:
        order.post_url = update_data["post_url"]
    if "notes" in update_data:
        order.notes = update_data["notes"]
    if "paid_at" in update_data:
        order.paid_at = datetime.fromisoformat(update_data["paid_at"])
    if "completed_at" in update_data:
        order.completed_at = datetime.fromisoformat(update_data["completed_at"])
    
    db.commit()
    db.refresh(order)
    
    return {
        "id": order.id,
        "status": order.status,
        "payment_method": order.payment_method,
        "payment_transaction_id": order.payment_transaction_id,
        "creative_content": order.creative_content,
        "creative_media_id": order.creative_media_id,
        "post_url": order.post_url
    }


# ============================================================================
# STATISTICS ENDPOINTS
# ============================================================================

@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get marketplace statistics"""
    total_users = db.query(User).count()
    total_channels = db.query(Channel).filter(Channel.status == "active").count()
    total_orders = db.query(Order).count()
    active_orders = db.query(Order).filter(
        Order.status.in_(["pending_payment", "paid", "processing"])
    ).count()
    
    return {
        "total_users": total_users,
        "total_channels": total_channels,
        "total_orders": total_orders,
        "active_orders": active_orders,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================================
# REVIEWS & RATINGS - PHASE 6 NEW
# ============================================================================

@app.post("/reviews/")
async def create_review(
    reviewer_telegram_id: int,
    reviewee_telegram_id: int,
    rating: int,
    comment: str = None,
    order_id: int = None,
    db: Session = Depends(get_db)
):
    """Create a review"""
    from models import Review, User
    
    # Get users
    reviewer = db.query(User).filter(User.telegram_id == reviewer_telegram_id).first()
    reviewee = db.query(User).filter(User.telegram_id == reviewee_telegram_id).first()
    
    if not reviewer or not reviewee:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create review
    review = Review(
        reviewer_id=reviewer.id,
        reviewee_id=reviewee.id,
        rating=rating,
        comment=comment,
        order_id=order_id
    )
    
    db.add(review)
    
    # Update reviewee's rating
    reviews = db.query(Review).filter(Review.reviewee_id == reviewee.id).all()
    avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else rating
    reviewee.rating = avg_rating
    
    db.commit()
    db.refresh(review)
    
    return {
        "id": review.id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat()
    }


@app.get("/reviews/user/{telegram_id}")
async def get_user_reviews(telegram_id: int, db: Session = Depends(get_db)):
    """Get all reviews for a user"""
    from models import Review, User
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return []
    
    reviews = db.query(Review).filter(Review.reviewee_id == user.id).all()
    
    result = []
    for review in reviews:
        reviewer = db.query(User).filter(User.id == review.reviewer_id).first()
        result.append({
            "id": review.id,
            "reviewer_name": reviewer.first_name if reviewer else "Unknown",
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at.isoformat()
        })
    
    return result


# ============================================================================
# DISCOUNT CODES - PHASE 6 NEW
# ============================================================================

@app.post("/discounts/")
async def create_discount_code(
    code: str,
    discount_type: str,
    discount_value: float,
    min_order_value: float = 0.0,
    max_uses: int = None,
    valid_until: str = None,
    db: Session = Depends(get_db)
):
    """Create a discount code"""
    from models import DiscountCode
    
    discount = DiscountCode(
        code=code.upper(),
        discount_type=discount_type,
        discount_value=discount_value,
        min_order_value=min_order_value,
        max_uses=max_uses,
        valid_until=datetime.fromisoformat(valid_until) if valid_until else None
    )
    
    db.add(discount)
    db.commit()
    db.refresh(discount)
    
    return {
        "id": discount.id,
        "code": discount.code,
        "discount_type": discount.discount_type,
        "discount_value": discount.discount_value
    }


@app.get("/discounts/{code}")
async def validate_discount_code(code: str, order_value: float, db: Session = Depends(get_db)):
    """Validate and apply discount code"""
    from models import DiscountCode
    
    discount = db.query(DiscountCode).filter(
        DiscountCode.code == code.upper(),
        DiscountCode.is_active == True
    ).first()
    
    if not discount:
        raise HTTPException(status_code=404, detail="Invalid discount code")
    
    # Check expiry
    if discount.valid_until and datetime.now(timezone.utc) > discount.valid_until:
        raise HTTPException(status_code=400, detail="Discount code expired")
    
    # Check max uses
    if discount.max_uses and discount.current_uses >= discount.max_uses:
        raise HTTPException(status_code=400, detail="Discount code limit reached")
    
    # Check minimum order value
    if order_value < discount.min_order_value:
        raise HTTPException(status_code=400, detail=f"Minimum order value is {discount.min_order_value}")
    
    # Calculate discount
    if discount.discount_type == "percentage":
        discount_amount = (order_value * discount.discount_value) / 100
    else:  # fixed
        discount_amount = discount.discount_value
    
    final_price = max(0, order_value - discount_amount)
    
    return {
        "valid": True,
        "discount_amount": discount_amount,
        "final_price": final_price,
        "code": discount.code
    }


# ============================================================================
# SCHEDULED POSTS - PHASE 6 NEW
# ============================================================================

@app.post("/scheduled-posts/")
async def create_scheduled_post(
    order_id: int,
    scheduled_time: str,
    db: Session = Depends(get_db)
):
    """Schedule a post for future posting"""
    from models import ScheduledPost
    
    scheduled_post = ScheduledPost(
        order_id=order_id,
        scheduled_time=datetime.fromisoformat(scheduled_time),
        status="pending"
    )
    
    db.add(scheduled_post)
    db.commit()
    db.refresh(scheduled_post)
    
    return {
        "id": scheduled_post.id,
        "order_id": scheduled_post.order_id,
        "scheduled_time": scheduled_post.scheduled_time.isoformat(),
        "status": scheduled_post.status
    }


@app.get("/scheduled-posts/pending")
async def get_pending_scheduled_posts(db: Session = Depends(get_db)):
    """Get all pending scheduled posts"""
    from models import ScheduledPost
    
    now = datetime.now(timezone.utc)
    posts = db.query(ScheduledPost).filter(
        ScheduledPost.status == "pending",
        ScheduledPost.scheduled_time <= now
    ).all()
    
    return [{"id": p.id, "order_id": p.order_id, "scheduled_time": p.scheduled_time.isoformat()} for p in posts]


# ============================================================================
# PACKAGE DEALS - PHASE 6 NEW
# ============================================================================

@app.post("/packages/")
async def create_package_deal(
    channel_id: int,
    name: str,
    ad_types: dict,
    original_price: float,
    package_price: float,
    description: str = None,
    db: Session = Depends(get_db)
):
    """Create a package deal"""
    from models import PackageDeal
    
    savings = original_price - package_price
    
    package = PackageDeal(
        channel_id=channel_id,
        name=name,
        description=description,
        ad_types=ad_types,
        original_price=original_price,
        package_price=package_price,
        savings=savings
    )
    
    db.add(package)
    db.commit()
    db.refresh(package)
    
    return {
        "id": package.id,
        "name": package.name,
        "package_price": package.package_price,
        "savings": package.savings
    }


@app.get("/packages/channel/{channel_id}")
async def get_channel_packages(channel_id: int, db: Session = Depends(get_db)):
    """Get all packages for a channel"""
    from models import PackageDeal
    
    packages = db.query(PackageDeal).filter(
        PackageDeal.channel_id == channel_id,
        PackageDeal.is_active == True
    ).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "ad_types": p.ad_types,
            "original_price": p.original_price,
            "package_price": p.package_price,
            "savings": p.savings
        }
        for p in packages
    ]


# ============================================================================
# ANALYTICS - PHASE 6 NEW
# ============================================================================

@app.get("/analytics/channel/{channel_id}")
async def get_channel_analytics(channel_id: int, days: int = 30, db: Session = Depends(get_db)):
    """Get channel analytics"""
    from models import ChannelAnalytics
    
    from_date = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=days)
    
    analytics = db.query(ChannelAnalytics).filter(
        ChannelAnalytics.channel_id == channel_id,
        ChannelAnalytics.date >= from_date
    ).all()
    
    return [
        {
            "date": a.date.isoformat(),
            "subscribers": a.subscribers,
            "total_views": a.total_views,
            "total_posts": a.total_posts,
            "avg_engagement": a.avg_engagement
        }
        for a in analytics
    ]


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
