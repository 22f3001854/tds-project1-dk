#!/bin/bash

# Test script for TDS Project 1 FastAPI application

echo "🧪 Testing TDS Project 1 FastAPI Application"
echo "============================================="

# Set test environment variables
export APP_SECRET="test-secret-123"
export GITHUB_TOKEN="dummy-token-for-testing"  
export GITHUB_OWNER="test-user"

echo "✅ Environment variables set"

# Activate virtual environment
source .venv/bin/activate

echo "✅ Virtual environment activated"

# Start server in background
echo "🚀 Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 7860 &
SERVER_PID=$!

# Wait for server to start
sleep 5

echo "🔍 Testing endpoints..."

# Test 1: Health endpoint
echo "Test 1: Health Check"
curl -s -X GET "http://localhost:7860/health" | python -m json.tool || echo "❌ Health endpoint failed"

# Test 2: Root endpoint
echo -e "\nTest 2: Root Endpoint"
curl -s -X GET "http://localhost:7860/" || echo "❌ Root endpoint failed"

# Test 3: Invalid request (should return 401)
echo -e "\nTest 3: Unauthorized Request"
curl -s -X POST "http://localhost:7860/handle_task" \
     -H "Content-Type: application/json" \
     -d '{"test": "invalid"}' || echo "Expected 401 error"

# Test 4: Valid structure but wrong secret
echo -e "\nTest 4: Wrong Secret"
curl -s -X POST "http://localhost:7860/handle_task" \
     -H "Content-Type: application/json" \
     -d '{
       "secret": "wrong-secret",
       "email": "test@example.com",
       "task": "sum-of-sales",
       "round": 1,
       "nonce": "test123",
       "evaluation_url": "https://httpbin.org/post"
     }' || echo "Expected 401 error"

# Clean up
echo -e "\n🛑 Stopping server..."
kill $SERVER_PID

echo "✅ Tests completed!"