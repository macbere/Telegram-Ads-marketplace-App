"""
main.py - FastAPI server
"""

from fastapi import FastAPI
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
    logger.info("🚀 Starting application...")
    bot_task = asyncio.create_task(bot.start_bot())
    yield
    logger.info("👋 Shutting down...")
    await bot.stop_bot()
    if not bot_task.done():
        bot_task.cancel()
    logger.info("✅ Application stopped")

app = FastAPI(title="Telegram Ads Marketplace", version="1.0", lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "Telegram Ads Marketplace",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
