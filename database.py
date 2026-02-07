"""
Database configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./telegram_ads_marketplace.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from models import Base
