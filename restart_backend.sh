#!/bin/bash

# Restart Backend Script for Smart Local Planner

echo "🔄 Restarting Smart Local Planner Backend..."

# Kill existing backend processes
echo "📋 Stopping existing backend processes..."
pkill -f "python main.py" || true
pkill -f "uvicorn" || true

# Wait a moment
sleep 2

# Navigate to backend directory and start
echo "🚀 Starting backend..."
cd /Users/zubair/Desktop/Dev/calendar-test
source .venv/bin/activate
cd planner/backend
python main.py &

echo "✅ Backend restarted successfully!"
echo "📍 Backend running at: http://127.0.0.1:8000"
echo "📚 API docs at: http://127.0.0.1:8000/docs"
