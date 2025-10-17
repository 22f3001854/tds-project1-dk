# Asynchronous Workflow Documentation

## Overview

The `/handle_task` endpoint now follows an **asynchronous processing model** to meet the requirement of returning 200 OK immediately while processing the task in the background.

## Workflow

### 1. Request Receipt (Immediate - <1 second)
```
Client → POST /handle_task
Server → Validates secret
Server → Returns 200 OK immediately
```

**Response:**
```json
{
  "status": "accepted",
  "message": "Task accepted and is being processed",
  "task": "sum-of-sales-001",
  "round": 1,
  "nonce": "abc123"
}
```

### 2. Background Processing (Asynchronous - Up to 10 minutes)
The server processes the task in a background thread:

1. **Create/Get Repository** (~2-3 seconds)
   - Creates new GitHub repo or retrieves existing one
   - Repository name: `tds-project1-{task}`

2. **Generate Files** (~5-60 seconds depending on LLM)
   - Generates HTML/JS using LLM (if available)
   - Falls back to templates if LLM unavailable
   - Generates README.md and LICENSE

3. **Upload Files** (~5-10 seconds)
   - Uploads all files to GitHub repository
   - Uses GitHub API with SHA-aware updates for Round 2+

4. **Enable GitHub Pages** (~2-3 seconds)
   - Enables GitHub Pages on main branch
   - Safe to call multiple times (handles 409 conflict)

5. **Post Evaluation** (~1-5 seconds with retry)
   - Posts results to `evaluation_url` from request
   - Uses exponential backoff (max 5 retries)
   - Max wait per retry: 16 seconds

### 3. Evaluation Callback (Automatic)
```
Server → POST {evaluation_url}
```

**Evaluation Payload:**
```json
{
  "email": "user@example.com",
  "task": "sum-of-sales-001",
  "round": 1,
  "nonce": "abc123",
  "repo_url": "https://github.com/owner/tds-project1-sum-of-sales-001",
  "commit_sha": "abc123def456...",
  "pages_url": "https://owner.github.io/tds-project1-sum-of-sales-001/",
  "status": "success"
}
```

## Timing Guarantees

| Operation | Estimated Time | Timeout |
|-----------|----------------|---------|
| Request acknowledgment | <1 second | N/A |
| GitHub API calls | 2-3 seconds each | 30s each |
| LLM generation | 5-60 seconds | 60s |
| File uploads | 5-10 seconds total | 30s per file |
| Evaluation post | 1-5 seconds | 30s |
| **Total Processing** | **~15 seconds - 6 minutes** | **<10 minutes** |

## Error Handling

### If Background Task Fails:
- Logs error to console
- Attempts to POST error to evaluation_url:
  ```json
  {
    "email": "user@example.com",
    "task": "sum-of-sales-001",
    "round": 1,
    "nonce": "abc123",
    "status": "error",
    "error": "Error message here"
  }
  ```

### If Evaluation Post Fails:
- Retries up to 5 times with exponential backoff
- Logs failure but doesn't crash the application
- Task is still completed (repo and pages are live)

## Benefits

1. ✅ **Immediate Response**: Client gets 200 OK instantly
2. ✅ **Non-blocking**: Server can handle multiple requests concurrently
3. ✅ **Reliable**: Exponential backoff ensures evaluation delivery
4. ✅ **Scalable**: Background tasks don't block the main thread
5. ✅ **Observable**: Detailed logging for monitoring
6. ✅ **Compliant**: Meets 10-minute requirement with room to spare

## Logging Output

```
✅ Request received for sum-of-sales-001, Round 1. Processing in background...
🚀 Background task started for sum-of-sales-001, Round 1
📦 Repository: https://github.com/owner/tds-project1-sum-of-sales-001
📝 Generated 4 files
✅ Uploaded: index.html
✅ Uploaded: data.csv
✅ Uploaded: README.md
✅ Uploaded: LICENSE
🌐 GitHub Pages enabled
📤 Posting evaluation to: https://evaluation.server/endpoint
✅ Evaluation posted successfully to https://evaluation.server/endpoint
✅ Task sum-of-sales-001 completed successfully!
```

## Code Implementation

### Key Components:

1. **BackgroundTasks** (FastAPI)
   - Built-in support for background task execution
   - Automatically manages thread lifecycle

2. **process_task_background()** function
   - Handles all GitHub operations
   - Posts to evaluation_url
   - Logs progress and errors

3. **Immediate 200 OK response**
   - Returns `{"status": "accepted"}` immediately
   - Includes task, round, and nonce for tracking

## Round 1 vs Round 2

Both rounds use the **same asynchronous workflow**:

- **Round 1**: Creates new repository
- **Round 2+**: Updates existing repository (same repo name)

The workflow handles both cases transparently.

## Testing

### Test Round 1:
```bash
curl -X POST https://your-app.hf.space/handle_task \
  -H "Content-Type: application/json" \
  -d @test_round1_request.json
```

**Expected Response:**
```json
{
  "status": "accepted",
  "message": "Task accepted and is being processed",
  "task": "sum-of-sales-round1-001",
  "round": 1,
  "nonce": "nonce-12345-round1-test"
}
```

Then check the evaluation_url for the final results within 10 minutes.

## Migration Notes

**Previous Behavior:**
- Client waited for entire processing to complete
- Could timeout if processing took too long
- Single-threaded blocking operation

**New Behavior:**
- Client gets immediate confirmation
- Processing happens in background
- Can handle multiple requests concurrently
- Evaluation results POSTed to callback URL
