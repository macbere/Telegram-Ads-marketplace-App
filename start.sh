#!/bin/bash

echo "=========================================="
echo "🚀 Telegram Ads Marketplace Startup"
echo "=========================================="

# Show environment info
echo "📋 Environment:"
echo "  - PORT: $PORT"
echo "  - BOT_TOKEN: ${BOT_TOKEN:0:20}...${BOT_TOKEN: -8}"

# Check if this is first boot (marker file doesn't exist)
if [ ! -f /tmp/not_first_boot ]; then
    echo ""
    echo "🕐 First boot detected - waiting 30 seconds for old instances to die..."
    sleep 30
    echo "✅ Wait complete"
    touch /tmp/not_first_boot
fi

# Clean up any hanging processes
echo "🧹 Cleaning up old processes..."
pkill -f "python.*main.py" || true
sleep 2
echo "✅ Cleanup complete"

echo ""
echo "🚀 Starting server on port $PORT..."

# Start the FastAPI server
python main.py
