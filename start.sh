#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Starting Telegram Ads Marketplace"
echo "=========================================="

# Kill any existing bot processes (important for restarts)
echo "🧹 Cleaning up any existing bot processes..."
pkill -f "python bot.py" || true
sleep 2

# Show environment info (without exposing full tokens)
echo "📊 Environment Check:"
echo "  PORT: $PORT"
echo "  API_URL: $API_URL"
echo "  BOT_TOKEN: ${BOT_TOKEN:0:15}...${BOT_TOKEN: -8}"

# Start FastAPI server in background
echo ""
echo "🌐 Starting FastAPI API server..."
uvicorn main:app --host 0.0.0.0 --port $PORT &
API_PID=$!

# Wait for API to start
echo "⏳ Waiting for API to initialize..."
sleep 8

# Check if API is running
if ps -p $API_PID > /dev/null; then
    echo "✅ API server is running (PID: $API_PID)"
else
    echo "❌ API server failed to start!"
    exit 1
fi

# Start Telegram bot (in FOREGROUND this time, not background)
echo ""
echo "🤖 Starting Telegram bot (foreground process)..."
python bot.py
