#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Telegram Ads Marketplace Startup"
echo "=========================================="

# Set default port if not provided
PORT=${PORT:-8000}

echo "📋 Environment Check:"
echo "  - PORT: $PORT"
echo "  - BOT_TOKEN: ${BOT_TOKEN:0:15}...${BOT_TOKEN: -8}"
echo "  - API_URL: $API_URL"
echo "  - DATABASE_URL: ${DATABASE_URL:0:30}..."
echo ""

# Kill any existing bot processes
echo "🧹 Cleaning up old processes..."
pkill -f "python bot.py" || true
pkill -f "python main.py" || true
sleep 2

# Start FastAPI in background
echo "🌐 Starting FastAPI server on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info &
API_PID=$!

echo "  ✅ API started (PID: $API_PID)"

# Wait for API to be ready
echo "⏳ Waiting for API to be ready (10 seconds)..."
sleep 10

# Check if API is still running
if ! ps -p $API_PID > /dev/null; then
    echo "❌ API failed to start - check logs above"
    exit 1
fi

echo "  ✅ API is healthy"
echo ""

# Start Telegram bot in foreground (this keeps the container alive)
echo "🤖 Starting Telegram bot (foreground process)..."
echo "=========================================="
exec python bot.py
