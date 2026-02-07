#!/bin/bash

echo "=========================================="
echo "🚀 Telegram Ads Marketplace"
echo "=========================================="

echo "📋 Environment:"
echo "  - PORT: $PORT"
echo "  - BOT_TOKEN: ${BOT_TOKEN:0:10}..."

echo "⏳ Starting in 5 seconds..."
sleep 5

echo "🚀 Starting server..."
python main.py
