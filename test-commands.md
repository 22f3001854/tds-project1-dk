# Example cURL Commands for Testing TDS Project 1

## Prerequisites
Make sure your FastAPI server is running:
```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

Set your environment variables:
```bash
export APP_SECRET="your-secret-key"
export GITHUB_TOKEN="your-github-token"  
export GITHUB_OWNER="your-github-username"
```

## Health Check
```bash
curl -X GET "http://localhost:7860/health"
```

## Round 1 Examples

### Round 1: Sum of Sales
```bash
curl -X POST "http://localhost:7860/handle_task" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your-secret-key",
    "email": "your@email.com",
    "task": "sales-demo-123",
    "round": 1,
    "nonce": "abc123def456",
    "evaluation_url": "https://httpbin.org/post",
    "brief": "sum-of-sales",
    "attachments": {}
  }'
```

### Round 1: Markdown to HTML
```bash
curl -X POST "http://localhost:7860/handle_task" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your-secret-key",
    "email": "your@email.com", 
    "task": "markdown-converter-456",
    "round": 1,
    "nonce": "xyz789uvw012",
    "evaluation_url": "https://httpbin.org/post",
    "brief": "markdown-to-html",
    "attachments": {}
  }'
```

### Round 1: GitHub User Created
```bash
curl -X POST "http://localhost:7860/handle_task" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your-secret-key",
    "email": "your@email.com",
    "task": "github-user-seed42",
    "round": 1, 
    "nonce": "mno345pqr678",
    "evaluation_url": "https://httpbin.org/post",
    "brief": "github-user-created",
    "attachments": {}
  }'
```

## Round 2 Examples

### Round 2: Update Sum of Sales
```bash
curl -X POST "http://localhost:7860/handle_task" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your-secret-key",
    "email": "your@email.com",
    "task": "sales-demo-123",
    "round": 2,
    "nonce": "def456ghi789", 
    "evaluation_url": "https://httpbin.org/post",
    "brief": "sum-of-sales",
    "attachments": {}
  }'
```

### Round 2: Update Markdown Converter
```bash
curl -X POST "http://localhost:7860/handle_task" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your-secret-key",
    "email": "your@email.com",
    "task": "markdown-converter-456", 
    "round": 2,
    "nonce": "uvw012jkl345",
    "evaluation_url": "https://httpbin.org/post",
    "brief": "markdown-to-html",
    "attachments": {}
  }'
```

### Round 2: Update GitHub User Checker  
```bash
curl -X POST "http://localhost:7860/handle_task" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your-secret-key",
    "email": "your@email.com",
    "task": "github-user-seed42",
    "round": 2,
    "nonce": "pqr678stu901",
    "evaluation_url": "https://httpbin.org/post", 
    "brief": "github-user-created",
    "attachments": {}
  }'
```

## Expected Response Format

All successful requests should return:
```json
{
  "status": "success",
  "repo_url": "https://github.com/your-username/tds-project1-task-name",
  "pages_url": "https://your-username.github.io/tds-project1-task-name/",
  "commit_sha": "abc123def456...",
  "round": 1
}
```

## Error Examples

### Invalid Secret
```bash
curl -X POST "http://localhost:7860/handle_task" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "wrong-secret",
    "email": "your@email.com",
    "task": "test-task",
    "round": 1,
    "nonce": "test123",
    "evaluation_url": "https://httpbin.org/post",
    "brief": "sum-of-sales"
  }'
```
Expected response: `{"detail": "Invalid secret"}` with status code 401

### Missing Required Fields
```bash
curl -X POST "http://localhost:7860/handle_task" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "your-secret-key",
    "email": "your@email.com"
  }'
```
Expected response: `{"detail": "Missing required fields: ['task', 'round', 'nonce', 'evaluation_url', 'brief']"}` with status code 400

### Invalid JSON
```bash
curl -X POST "http://localhost:7860/handle_task" \
  -H "Content-Type: application/json" \
  -d '{"invalid": json}'
```
Expected response: `{"detail": "Invalid JSON in request body"}` with status code 400

## Testing with Real TDS Server

When testing with the actual TDS server, replace:
- `"your-secret-key"` with your actual APP_SECRET
- `"your@email.com"` with your actual email
- `"https://httpbin.org/post"` with the real evaluation URL provided by TDS
- Task names and nonces with values provided by TDS

## Verification Steps

After running a successful request:

1. **Check GitHub Repository**: Visit the `repo_url` to see the created repository
2. **Check GitHub Pages**: Visit the `pages_url` to see the deployed site (may take a few minutes)
3. **Check Evaluation**: Verify the evaluation endpoint received the POST request
4. **Check Files**: Repository should contain:
   - `index.html` (main site file)
   - `README.md` (project documentation)
   - `LICENSE` (MIT license)
   - Additional files based on the brief (e.g., `data.csv` for sum-of-sales)

## Notes

- GitHub Pages may take 5-10 minutes to deploy after initial setup
- Repository names are automatically generated as `tds-project1-{task}`
- Round 2 requests will update the existing repository rather than creating a new one
- All files are uploaded with proper commit messages indicating the round number