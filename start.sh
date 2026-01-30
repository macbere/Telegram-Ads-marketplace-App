#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Telegram Ads Marketplace Startup"
echo "=========================================="

PORT=${PORT:-10000}

echo "📋 Environment:"
echo "  - PORT: $PORT"
echo "  - BOT_TOKEN: ${BOT_TOKEN:0:15}...${BOT_TOKEN: -8}"
echo ""

# Kill any zombie processes
echo "🧹 Cleaning up old processes..."
pkill -9 -f "uvicorn" 2>/dev/null || true
pkill -9 -f "python" 2>/dev/null || true
sleep 2

echo "✅ Cleanup complete"
echo ""
echo "🚀 Starting server on port $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info --timeout-keep-alive 75
