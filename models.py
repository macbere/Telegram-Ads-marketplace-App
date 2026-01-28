"""
models.py - Database models for the Telegram Ads Marketplace
Defines all tables: Users, Channels, Deals, Posts, and ChannelStats
"""

from sqlalchemy import Column, Integer, String, BigInteger, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime, timedelta


class User(Base):
    """
    Stores Telegram users (both channel owners and advertisers)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)  # Telegram user ID
    username = Column(String, nullable=True)  # @username
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(String, default="user")  # "channel_owner", "advertiser", or "both"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owned_channels = relationship("Channel", back_populates="owner")
    deals_as_advertiser = relationship("Deal", foreign_keys="Deal.advertiser_id", back_populates="advertiser")


class Channel(Base):
    """
    Stores listed channels with their pricing and stats
    """
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Channel identification
    telegram_channel_id = Column(BigInteger, unique=True, index=True, nullable=False)  # Channel ID from Telegram
    channel_username = Column(String, nullable=True)  # @channelname
    channel_title = Column(String, nullable=False)
    channel_description = Column(Text, nullable=True)
    
    # Bot admin status
    bot_is_admin = Column(Boolean, default=False)  # Has our bot been added as admin?
    bot_added_at = Column(DateTime(timezone=True), nullable=True)
    
    # Pricing for different ad formats (JSON for flexibility)
    pricing = Column(JSON, nullable=False)  # {"post": 100, "story": 50, "repost": 30}
    
    # Channel stats (updated periodically from Telegram)
    subscribers = Column(Integer, default=0)
    avg_views = Column(Integer, default=0)
    avg_reach = Column(Integer, default=0)
    
    # Status
    status = Column(String, default="pending")  # pending, active, suspended
    is_verified = Column(Boolean, default=False)  # Bot verified as admin
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="owned_channels")
    deals = relationship("Deal", back_populates="channel")
    stats_history = relationship("ChannelStats", back_populates="channel")


class ChannelStats(Base):
    """
    Stores historical channel statistics fetched from Telegram
    """
    __tablename__ = "channel_stats"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    
    # Stats from Telegram API
    subscribers = Column(Integer, nullable=False)
    avg_views = Column(Integer, default=0)
    avg_reach = Column(Integer, default=0)
    language_stats = Column(JSON, nullable=True)  # {"en": 70, "ru": 30}
    premium_percentage = Column(Float, default=0)  # % of premium users
    
    # Additional metrics
    engagement_rate = Column(Float, default=0)
    
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    channel = relationship("Channel", back_populates="stats_history")


class Deal(Base):
    """
    Stores escrow deals between advertisers and channel owners
    """
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    
    # Parties involved
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    
    # Deal details
    ad_format = Column(String, nullable=False)  # "post", "story", "repost"
    price = Column(Float, nullable=False)  # Price in TON or USD
    currency = Column(String, default="TON")
    
    # Campaign brief
    brief = Column(Text, nullable=True)  # Advertiser's requirements
    
    # Deal status workflow
    status = Column(String, default="pending")  
    # Status flow: pending → accepted → creative_submitted → creative_approved → posted → verified → completed
    # Or: pending → rejected, or any status → cancelled, or any → refunded
    
    # Escrow information
    escrow_wallet = Column(String, nullable=True)  # Unique wallet address for this deal
    payment_tx_hash = Column(String, nullable=True)  # Transaction hash of payment
    payment_received = Column(Boolean, default=False)
    funds_released = Column(Boolean, default=False)
    release_tx_hash = Column(String, nullable=True)
    
    # Timing
    scheduled_post_time = Column(DateTime(timezone=True), nullable=True)  # When to post
    posted_at = Column(DateTime(timezone=True), nullable=True)  # When actually posted
    post_message_id = Column(BigInteger, nullable=True)  # Telegram message ID of posted ad
    
    # Verification - ensure post stays live for minimum duration
    min_duration_hours = Column(Integer, default=24)  # Post must stay live for X hours
    verified_at = Column(DateTime(timezone=True), nullable=True)  # When we verified it's still live
    
    # Timeout/cancellation
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    timeout_hours = Column(Integer, default=72)  # Auto-cancel if no activity for X hours
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    advertiser = relationship("User", foreign_keys=[advertiser_id], back_populates="deals_as_advertiser")
    channel = relationship("Channel", back_populates="deals")
    posts = relationship("Post", back_populates="deal")


class Post(Base):
    """
    Stores creative submissions and approvals for each deal
    """
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    
    # Creative content
    content_type = Column(String, nullable=False)  # "text", "photo", "video"
    content_text = Column(Text, nullable=True)  # Post text/caption
    media_url = Column(String, nullable=True)  # URL to uploaded media
    media_file_id = Column(String, nullable=True)  # Telegram file_id for media
    
    # Approval workflow
    status = Column(String, default="draft")  # draft → submitted → approved → rejected
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who submitted (channel owner)
    
    # Review
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Advertiser who reviewed
    review_notes = Column(Text, nullable=True)  # Feedback from advertiser
    
    # Version tracking (if advertiser requests edits)
    version = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    deal = relationship("Deal", back_populates="posts")


class ChannelAdmin(Base):
    """
    Stores multiple admins/PR managers for a channel (EXTRA feature)
    """
    __tablename__ = "channel_admins"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Admin rights (fetched from Telegram)
    can_post = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    last_verified_at = Column(DateTime(timezone=True), server_default=func.now())  # Re-check periodically
    is_active = Column(Boolean, default=True)  # Still an admin?
