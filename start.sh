#!/bin/bash

echo "🚀 Starting Telegram Ads Marketplace (Webhook Mode)"
echo "=================================================="

# Just start the FastAPI server - no separate bot process needed!
uvicorn main:app --host 0.0.0.0 --port $PORT
