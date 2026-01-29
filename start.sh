#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Starting Telegram Ads Marketplace"
echo "=========================================="

# Show environment info (without exposing full tokens)
echo "📊 Environment Check:"
echo "  PORT: $PORT"
echo "  API_URL: $API_URL"
echo "  BOT_TOKEN: ${BOT_TOKEN:0:15}...${BOT_TOKEN: -8}"
echo "  DATABASE_URL: ${DATABASE_URL:0:30}..."

# Start FastAPI server in background
echo ""
echo "🌐 Starting FastAPI API server..."
uvicorn main:app --host 0.0.0.0 --port $PORT &
API_PID=$!

# Wait for API to start
echo "⏳ Waiting for API to initialize (10 seconds)..."
sleep 10

# Check if API is running
if ps -p $API_PID > /dev/null; then
    echo "✅ API server is running (PID: $API_PID)"
else
    echo "❌ API server failed to start!"
    exit 1
fi

# Test API connectivity
echo ""
echo "🧪 Testing API endpoint..."
curl -s http://localhost:$PORT/ || echo "⚠️  API health check failed (may still be starting)"

# Give network a moment to stabilize
echo ""
echo "⏳ Waiting for network to stabilize (5 seconds)..."
sleep 5

# Start Telegram bot
echo ""
echo "🤖 Starting Telegram bot..."
python bot.py &
BOT_PID=$!

# Wait a moment and check if bot started successfully
sleep 3
if ps -p $BOT_PID > /dev/null; then
    echo "✅ Bot process is running (PID: $BOT_PID)"
else
    echo "⚠️  Bot process exited, check logs above"
fi

# Keep both running
echo ""
echo "=========================================="
echo "✅ Services started successfully!"
echo "   API PID: $API_PID"
echo "   Bot PID: $BOT_PID"
echo "=========================================="

# Wait for API (main process)
wait $API_PID
