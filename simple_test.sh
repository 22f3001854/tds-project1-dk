#!/bin/bash

echo "🧪 Simple FastAPI Test"
echo "====================="

# Set environment variables
export APP_SECRET="test-secret-123"
export GITHUB_TOKEN="dummy-token"
export GITHUB_OWNER="test-user"

# Activate virtual environment
source .venv/bin/activate

# Start server
echo "🚀 Starting server..."
uvicorn main:app --host 0.0.0.0 --port 7860 &
SERVER_PID=$!

# Wait for startup
sleep 3

echo "📡 Testing basic endpoints..."

# Test health endpoint
echo "Health check:"
curl -s "http://localhost:7860/health" | python3 -m json.tool

echo -e "\nRoot endpoint:"
curl -s "http://localhost:7860/"

echo -e "\nAPI docs available at: http://localhost:7860/docs"

# Stop server
echo -e "\n🛑 Stopping server..."
kill $SERVER_PID
wait $SERVER_PID 2>/dev/null

echo "✅ Basic tests completed!"