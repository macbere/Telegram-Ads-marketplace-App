#!/bin/bash

echo "=========================================="
echo "🚀 Telegram Ads Marketplace Startup"
echo "=========================================="

# Show environment info
echo "📋 Environment:"
echo "  - PORT: $PORT"
echo "  - BOT_TOKEN: ${BOT_TOKEN:0:20}...${BOT_TOKEN: -8}"

# NUCLEAR CLEANUP - kill everything
echo "🧹 NUCLEAR CLEANUP..."
pkill -9 -f "python" || true
pkill -9 -f "python3" || true
sleep 10

# Clean Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Wait for old processes to die
echo "🕐 Waiting 60 seconds for old instances to die..."
sleep 60
echo "✅ Wait complete"

echo ""
echo "🚀 Starting server on port $PORT..."

# Start the FastAPI server
python main.py
