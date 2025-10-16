# Testing Guide for TDS Project 1 - FastAPI LLM Code Deployment

## ✅ Testing Status Summary

**Basic functionality:** ✅ Working  
**Health endpoint:** ✅ Working  
**Root endpoint:** ✅ Working  
**Error handling:** ✅ Working  

## Prerequisites

1. **Environment Setup:**
   ```bash
   # Set your actual values
   export APP_SECRET="your-secret-key"
   export GITHUB_TOKEN="your-github-personal-access-token"
   export GITHUB_OWNER="your-github-username"
   ```

2. **Virtual Environment:**
   ```bash
   source .venv/bin/activate
   ```

## Quick Testing

### 1. Start the Server
```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

### 2. Test Basic Endpoints

**Health Check:**
```bash
curl -X GET "http://localhost:7860/health"
# Expected: {"status":"healthy","github_owner":"...","has_github_token":true,"has_app_secret":true}
```

**Root Endpoint:**
```bash
curl -X GET "http://localhost:7860/"
# Expected: {"message":"TDS Project 1 - LLM Code Deployment API","status":"running"}
```

**API Documentation:**
Open http://localhost:7860/docs in your browser for interactive API docs.

### 3. Test Main Endpoint

**Test with wrong secret (should return 401):**
```bash
curl -X POST "http://localhost:7860/handle_task" \
     -H "Content-Type: application/json" \
     -d '{
       "secret": "wrong-secret",
       "email": "test@example.com",
       "task": "sum-of-sales",
       "brief": "Sum sales data",
       "round": 1,
       "nonce": "test123",
       "evaluation_url": "https://httpbin.org/post"
     }'
# Expected: 401 Unauthorized
```

**Test with correct secret (requires valid GitHub token):**
```bash
curl -X POST "http://localhost:7860/handle_task" \
     -H "Content-Type: application/json" \
     -d '{
       "secret": "'$APP_SECRET'",
       "email": "your-email@example.com",
       "task": "sum-of-sales",
       "brief": "Create a simple sales calculator",
       "round": 1,
       "nonce": "test123",
       "evaluation_url": "https://httpbin.org/post"
     }'
```

## Automated Testing Scripts

We've created test scripts for you:

### Simple Test
```bash
./simple_test.sh
```
Tests basic functionality and endpoints.

### Comprehensive Test
```bash
./test_app.sh
```
Tests all endpoints including error cases.

## Testing Different Tasks

The application supports three main tasks:

1. **sum-of-sales** - Creates a sales data calculator
2. **markdown-to-html** - Creates a markdown renderer  
3. **github-user-created** - Creates a GitHub user lookup tool

## Expected Behavior

### Round 1
- Creates a new GitHub repository
- Generates HTML/JS files based on the task
- Enables GitHub Pages
- Returns repository URL and commit SHA

### Round 2  
- Updates the existing repository
- Adds or modifies files
- Returns updated commit SHA

## Troubleshooting

### Common Issues:

1. **Port already in use:** Kill existing servers with `pkill -f uvicorn`
2. **Missing environment variables:** Check that APP_SECRET, GITHUB_TOKEN, and GITHUB_OWNER are set
3. **GitHub API errors:** Ensure your GITHUB_TOKEN has repo creation permissions

### Debug Mode:
Add `--reload` to see code changes in real-time:
```bash
uvicorn main:app --host 0.0.0.0 --port 7860 --reload
```

## Security Notes

- Never commit your real GITHUB_TOKEN to version control
- Use environment variables for all sensitive data
- The APP_SECRET should be shared only with the TDS server

## Next Steps

1. Set up your real GitHub token with appropriate permissions
2. Test with actual TDS server requests
3. Deploy to Hugging Face Spaces or similar platform

Your FastAPI application is ready for production testing! 🚀