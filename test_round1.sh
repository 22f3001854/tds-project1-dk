#!/bin/bash

# Test script for Round 1 - Sum of Sales task
# This sends a round 1 request to the FastAPI application

# Configuration
API_URL="${API_URL:-http://localhost:7860/handle_task}"
REQUEST_FILE="test_round1_request.json"

echo "=========================================="
echo "Testing Round 1: Sum of Sales"
echo "=========================================="
echo ""
echo "API Endpoint: $API_URL"
echo "Request File: $REQUEST_FILE"
echo ""

# Check if request file exists
if [ ! -f "$REQUEST_FILE" ]; then
    echo "❌ Error: Request file '$REQUEST_FILE' not found!"
    exit 1
fi

# Display the request payload
echo "📤 Request Payload:"
cat "$REQUEST_FILE" | jq '.'
echo ""

# Send the request
echo "🚀 Sending request..."
echo ""

response=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d @"$REQUEST_FILE")

# Display the response
echo "📥 Response:"
echo "$response" | jq '.'
echo ""

# Extract key information
status=$(echo "$response" | jq -r '.status // "error"')
repo_url=$(echo "$response" | jq -r '.repo_url // "N/A"')
pages_url=$(echo "$response" | jq -r '.pages_url // "N/A"')

echo "=========================================="
echo "Summary:"
echo "=========================================="
echo "Status: $status"
echo "Repository: $repo_url"
echo "GitHub Pages: $pages_url"
echo ""

if [ "$status" = "success" ]; then
    echo "✅ Round 1 request completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Visit the GitHub repository: $repo_url"
    echo "2. Wait ~1 minute for GitHub Pages to deploy"
    echo "3. Open the live page: $pages_url"
    echo ""
else
    echo "❌ Round 1 request failed!"
    echo ""
    echo "Check the error message above for details."
    exit 1
fi
