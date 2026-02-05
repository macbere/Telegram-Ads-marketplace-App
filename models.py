"""
Database models for Telegram Ads Marketplace - FIXED for large Telegram IDs
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Boolean, Text, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model - Telegram users (both channel owners and advertisers)"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)  # FIXED: BigInteger
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    is_channel_owner = Column(Boolean, default=False)
    is_advertiser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owned_channels = relationship("Channel", back_populates="owner", foreign_keys="Channel.owner_id")
    deals_as_advertiser = relationship("Deal", back_populates="advertiser", foreign_keys="Deal.advertiser_id")
    orders = relationship("Order", back_populates="buyer", foreign_keys="Order.buyer_id")


class Channel(Base):
    """Channel model - Telegram channels listed for advertising"""
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_channel_id = Column(BigInteger, unique=True, index=True, nullable=False)  # FIXED: BigInteger
    channel_title = Column(String, nullable=False)
    channel_username = Column(String, nullable=True)
    subscribers = Column(Integer, default=0)
    avg_views = Column(Integer, default=0)
    pricing = Column(JSON, nullable=False)  # {"post": 100.0, "story": 50.0, "repost": 25.0}
    status = Column(String, default="active")  # active, inactive, suspended
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="owned_channels", foreign_keys=[owner_id])
    deals = relationship("Deal", back_populates="channel")
    stats = relationship("ChannelStats", back_populates="channel", uselist=False)
    orders = relationship("Order", back_populates="channel")


class Deal(Base):
    """Deal model - Advertising deals between advertisers and channels"""
    __tablename__ = "deals"
    
    id = Column(Integer, primary_key=True, index=True)
    advertiser_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    ad_type = Column(String, nullable=False)  # post, story, repost
    price = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, accepted, creative_submitted, creative_approved, posted, completed, cancelled
    creative_content = Column(Text, nullable=True)  # Ad content/text
    creative_media_id = Column(String, nullable=True)  # Telegram file_id for image/video
    post_url = Column(String, nullable=True)  # URL of posted ad
    created_at = Column(DateTime, default=datetime.utcnow)
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
    status = Column(String, default="pending_payment")  # pending_payment, paid, processing, completed, cancelled, refunded
    payment_method = Column(String, nullable=True)  # crypto, card, etc.
    payment_transaction_id = Column(String, nullable=True)
    creative_content = Column(Text, nullable=True)
    creative_media_id = Column(String, nullable=True)
    post_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
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
    telegram_post_id = Column(BigInteger, nullable=False)  # FIXED: BigInteger
    post_url = Column(String, nullable=False)
    posted_at = Column(DateTime, default=datetime.utcnow)
    views = Column(Integer, default=0)
    last_checked = Column(DateTime, default=datetime.utcnow)
    
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
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    channel = relationship("Channel", back_populates="stats")
