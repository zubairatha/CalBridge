#!/bin/bash

# Restart Frontend Script for Smart Local Planner

echo "🔄 Restarting Smart Local Planner Frontend..."

# Kill existing frontend processes
echo "📋 Stopping existing frontend processes..."
pkill -f "npm run dev" || true
pkill -f "vite" || true

# Wait a moment
sleep 2

# Navigate to frontend directory and start
echo "🚀 Starting frontend..."
cd /Users/zubair/Desktop/Dev/calendar-test
source .venv/bin/activate
cd planner-frontend
npm run dev &

echo "✅ Frontend restarted successfully!"
echo "📍 Frontend running at: http://localhost:5173"
