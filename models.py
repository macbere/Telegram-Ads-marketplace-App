"""
Database models for Telegram Ads Marketplace - PHASE 6: PREMIUM PACKAGE
Enhanced with ratings, reviews, analytics, scheduled posts, and more
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Boolean, Text, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class User(Base):
    """User model - Telegram users (both channel owners and advertisers)"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    is_channel_owner = Column(Boolean, default=False)
    is_advertiser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)  # NEW: Verification badge
    rating = Column(Float, default=0.0)  # NEW: User rating (0-5)
    total_spent = Column(Float, default=0.0)  # NEW: Total money spent
    total_earned = Column(Float, default=0.0)  # NEW: Total money earned
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    owned_channels = relationship("Channel", back_populates="owner", foreign_keys="Channel.owner_id")
    deals_as_advertiser = relationship("Deal", back_populates="advertiser", foreign_keys="Deal.advertiser_id")
    orders = relationship("Order", back_populates="buyer", foreign_keys="Order.buyer_id")
    reviews_given = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_id")
    reviews_received = relationship("Review", back_populates="reviewee", foreign_keys="Review.reviewee_id")


class Channel(Base):
    """Channel model - Telegram channels listed for advertising"""
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_channel_id = Column(BigInteger, unique=True, index=True, nullable=False)
    channel_title = Column(String, nullable=False)
    channel_username = Column(String, nullable=True)
    category = Column(String, default="general")  # NEW: Category (crypto, gaming, tech, etc.)
    subscribers = Column(Integer, default=0)
    avg_views = Column(Integer, default=0)
    pricing = Column(JSON, nullable=False)  # {"post": 100.0, "story": 50.0, "repost": 25.0}
    status = Column(String, default="active")  # active, inactive, suspended
    is_verified = Column(Boolean, default=False)  # NEW: Verified channel badge
    is_premium = Column(Boolean, default=False)  # NEW: Premium listing
    rating = Column(Float, default=0.0)  # NEW: Channel rating (0-5)
    total_orders = Column(Integer, default=0)  # NEW: Total orders completed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    owner = relationship("User", back_populates="owned_channels", foreign_keys=[owner_id])
    deals = relationship("Deal", back_populates="channel")
    stats = relationship("ChannelStats", back_populates="channel", uselist=False)
    orders = relationship("Order", back_populates="channel")
    analytics = relationship("ChannelAnalytics", back_populates="channel")  # NEW


class Deal(Base):
    """Deal model - Advertising deals between advertisers and channels"""
    __tablename__ = "deals"
    
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    ad_type = Column(String, nullable=False)  # post, story, repost
    price = Column(Float, nullable=False)
    status = Column(String, default="pending")
    creative_content = Column(Text, nullable=True)
    creative_media_id = Column(String, nullable=True)
    post_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    advertiser = relationship("User", back_populates="deals_as_advertiser", foreign_keys=[advertiser_id])
    channel = relationship("Channel", back_populates="deals")
    posts = relationship("Post", back_populates="deal")


class Order(Base):
    """Order model - Purchase orders for ad slots"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    ad_type = Column(String, nullable=False)  # post, story, repost
    price = Column(Float, nullable=False)
    discount_code = Column(String, nullable=True)  # NEW: Applied discount code
    discount_amount = Column(Float, default=0.0)  # NEW: Discount applied
    final_price = Column(Float, nullable=False)  # NEW: Price after discount
    status = Column(String, default="pending_payment")
    payment_method = Column(String, nullable=True)
    payment_transaction_id = Column(String, nullable=True)
    creative_content = Column(Text, nullable=True)
    creative_media_id = Column(String, nullable=True)
    scheduled_post_time = Column(DateTime, nullable=True)  # NEW: Scheduled posting
    post_url = Column(String, nullable=True)
    post_views = Column(Integer, default=0)  # NEW: Track views
    notes = Column(Text, nullable=True)
    
    # CONTEST MVP: Escrow system (simulated)
    escrow_status = Column(String, default="pending")  # pending, held, released, refunded
    escrow_held_at = Column(DateTime, nullable=True)
    escrow_released_at = Column(DateTime, nullable=True)
    escrow_amount = Column(Float, nullable=True)
    
    # CONTEST MVP: Delivery confirmation
    delivery_confirmed = Column(Boolean, default=False)
    delivery_confirmed_at = Column(DateTime, nullable=True)
    delivery_confirmed_by = Column(String, nullable=True)  # buyer or auto
    
    # CONTEST MVP: Auto-posting
    auto_posted = Column(Boolean, default=False)
    auto_posted_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    paid_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    buyer = relationship("User", back_populates="orders", foreign_keys=[buyer_id])
    channel = relationship("Channel", back_populates="orders")


class Post(Base):
    """Post model - Actual posts made as part of deals"""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    telegram_post_id = Column(BigInteger, nullable=False)
    post_url = Column(String, nullable=False)
    posted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)  # NEW: Track likes
    shares = Column(Integer, default=0)  # NEW: Track shares
    last_checked = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    deal = relationship("Deal", back_populates="posts")


class ChannelStats(Base):
    """ChannelStats model - Statistics for channels"""
    __tablename__ = "channel_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), unique=True, nullable=False)
    total_deals = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)
    avg_rating = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    channel = relationship("Channel", back_populates="stats")


# ============================================================================
# NEW MODELS FOR PREMIUM FEATURES
# ============================================================================

class Review(Base):
    """Review model - User ratings and reviews"""
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who gave the review
    reviewee_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who received the review
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Related order
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)  # Written review
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    reviewer = relationship("User", back_populates="reviews_given", foreign_keys=[reviewer_id])
    reviewee = relationship("User", back_populates="reviews_received", foreign_keys=[reviewee_id])


class DiscountCode(Base):
    """DiscountCode model - Promo codes and discounts"""
    __tablename__ = "discount_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)  # e.g., "WELCOME10"
    discount_type = Column(String, nullable=False)  # "percentage" or "fixed"
    discount_value = Column(Float, nullable=False)  # 10 (for 10%) or 5.0 (for $5 off)
    min_order_value = Column(Float, default=0.0)  # Minimum order amount
    max_uses = Column(Integer, nullable=True)  # Max number of uses (null = unlimited)
    current_uses = Column(Integer, default=0)  # Times used
    valid_from = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    valid_until = Column(DateTime, nullable=True)  # Expiry date
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChannelAnalytics(Base):
    """ChannelAnalytics model - Daily analytics for channels"""
    __tablename__ = "channel_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    subscribers = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    total_posts = Column(Integer, default=0)
    avg_engagement = Column(Float, default=0.0)  # Engagement rate %
    
    # Relationships
    channel = relationship("Channel", back_populates="analytics")


class ScheduledPost(Base):
    """ScheduledPost model - Posts scheduled for future posting"""
    __tablename__ = "scheduled_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String, default="pending")  # pending, posted, failed
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatMessage(Base):
    """ChatMessage model - In-app messaging between users"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Related order
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PackageDeal(Base):
    """PackageDeal model - Bundled ad packages"""
    __tablename__ = "package_deals"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g., "Starter Pack"
    description = Column(Text, nullable=True)
    ad_types = Column(JSON, nullable=False)  # {"post": 3, "story": 5, "repost": 10}
    original_price = Column(Float, nullable=False)
    package_price = Column(Float, nullable=False)
    savings = Column(Float, nullable=False)  # How much saved
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
