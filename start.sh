#!/bin/bash

echo "=========================================="
echo "🚀 Telegram Ads Marketplace"
echo "=========================================="

echo "📋 Environment:"
echo "  - PORT: $PORT"
echo "  - BOT_TOKEN: ${BOT_TOKEN:0:10}..."

echo "🧹 Killing old processes..."
pkill -9 -f "python" || true
pkill -9 -f "python3" || true
sleep 10

echo "⏳ Starting in 15 seconds..."
sleep 15

echo "🚀 Starting server..."
python main.py
