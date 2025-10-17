#!/bin/bash

# Test captcha-solver request with new format including 'checks' field

echo "Testing captcha-solver task with new request format..."
echo "=================================================="
echo ""

curl -X POST http://127.0.0.1:7860/handle_task \
  -H "Content-Type: application/json" \
  -d @test_captcha_request.json \
  --silent --show-error | jq .

echo ""
echo "=================================================="
echo "Test completed!"
