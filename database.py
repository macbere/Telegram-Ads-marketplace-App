"""
Database configuration and initialization
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://telegram_ads_database_user:lZAkenQdwSEmF5ITMI1odTcu6ku2Pnnl@dpg-d62di45actks73bvacgg-a/telegram_ads_database"
)

logger.info(f"🔗 Database URL: {DATABASE_URL[:30]}...")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables"""
    from models import Base
    
    try:
        logger.info("📊 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        # Test connection (SQLAlchemy 2.0 syntax)
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            logger.info("✅ Database connection verified")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
