#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Telegram Ads Marketplace"
echo "=========================================="

# Start FastAPI in background
echo "🌐 Starting API server..."
uvicorn main:app --host 0.0.0.0 --port $PORT &
API_PID=$!

# Wait for API to be ready
sleep 8

# Verify API started
if ! ps -p $API_PID > /dev/null; then
    echo "❌ API failed to start"
    exit 1
fi

echo "✅ API running (PID: $API_PID)"

# Start bot in foreground (main process)
echo "🤖 Starting Telegram bot..."
exec python bot.py
