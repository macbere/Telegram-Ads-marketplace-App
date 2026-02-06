#!/bin/bash

echo "=========================================="
echo "🚀 Telegram Ads Marketplace Startup"
echo "=========================================="

# Show environment info
echo "📋 Environment:"
echo "  - PORT: $PORT"
echo "  - BOT_TOKEN: ${BOT_TOKEN:0:20}...${BOT_TOKEN: -8}"

# Wait a bit for network
echo "⏳ Waiting 10 seconds for network..."
sleep 10

echo ""
echo "🚀 Starting server on port $PORT..."

# Start the FastAPI server - Render will handle port binding
python main.py
