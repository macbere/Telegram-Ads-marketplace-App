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

# CRITICAL: Wait on first boot to let old instances die
if [ ! -f /tmp/first_boot_done ]; then
    echo "🕐 First boot detected - waiting 30 seconds for old instances to die..."
    sleep 30
    touch /tmp/first_boot_done
    echo "✅ Wait complete"
fi

# Kill any zombie processes
echo "🧹 Cleaning up old processes..."
pkill -9 -f "uvicorn" 2>/dev/null || true
pkill -9 -f "python" 2>/dev/null || true
sleep 2

echo "✅ Cleanup complete"
echo ""
echo "🚀 Starting server on port $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info --timeout-keep-alive 75
