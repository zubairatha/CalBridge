#!/bin/bash

# Restart All Services Script for Smart Local Planner

echo "🔄 Restarting all Smart Local Planner services..."

# Kill all existing processes
echo "📋 Stopping all existing processes..."
pkill -f "python main.py" || true
pkill -f "uvicorn" || true
pkill -f "npm run dev" || true
pkill -f "vite" || true

# Wait a moment
sleep 3

# Start backend
echo "🚀 Starting backend..."
cd /Users/zubair/Desktop/Dev/calendar-test
source .venv/bin/activate
cd planner/backend
python main.py &

# Wait for backend to start
sleep 3

# Start frontend
echo "🚀 Starting frontend..."
cd /Users/zubair/Desktop/Dev/calendar-test
source .venv/bin/activate
cd planner-frontend
npm run dev &

echo "✅ All services restarted successfully!"
echo "📍 Backend: http://127.0.0.1:8000"
echo "📍 Frontend: http://localhost:5173"
echo "📚 API docs: http://127.0.0.1:8000/docs"
