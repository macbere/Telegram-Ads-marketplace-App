#!/bin/bash

# Start FastAPI server in background
uvicorn main:app --host 0.0.0.0 --port $PORT &

# Wait a moment for API to start
sleep 5

# Start Telegram bot
python bot.py
