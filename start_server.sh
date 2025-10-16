#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    source .env
else
    echo "Warning: .env file not found. Using existing environment variables."
fi

# Activate virtual environment
source .venv/bin/activate

# Start server
echo "Starting server with environment variables:"
echo "APP_SECRET: ${APP_SECRET:0:10}..."
echo "GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..."
echo "GITHUB_OWNER: ${GITHUB_OWNER}"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
echo ""

uvicorn main:app --port 7860
