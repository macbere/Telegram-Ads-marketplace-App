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
echo ""

# NUCLEAR OPTION: Kill EVERYTHING Python-related
echo "🧹 KILLING ALL PYTHON PROCESSES..."
killall python python3 || true
killall -9 python python3 || true
pkill -9 -f "bot.py" || true
pkill -9 -f "main.py" || true
pkill -9 -f "uvicorn" || true

# Wait to ensure everything is dead
echo "⏳ Waiting 5 seconds for processes to die..."
sleep 5

# Verify nothing is running
echo "🔍 Checking for remaining Python processes..."
ps aux | grep python || echo "✅ No Python processes found"

# Start FastAPI in background
echo ""
echo "🌐 Starting FastAPI server on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port $PORT --log-level warning &
API_PID=$!

echo "  ✅ API started (PID: $API_PID)"

# Wait for API to be ready
echo "⏳ Waiting for API to be ready (8 seconds)..."
sleep 8

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
