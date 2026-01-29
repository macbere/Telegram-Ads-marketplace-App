#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Starting Telegram Ads Marketplace"
echo "=========================================="

PORT=${PORT:-8000}

echo "Starting single-process server on port $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info
