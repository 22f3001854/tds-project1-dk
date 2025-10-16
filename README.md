# TDS Project 1 - LLM Code Deployment

A FastAPI application that handles GitHub repository creation, file uploads, and GitHub Pages setup for the TDS LLM Code Deployment project.

## Features

- **POST `/handle_task`**: Main endpoint for processing TDS server requests
- **GitHub Integration**: Automatic repository creation and file uploads
- **GitHub Pages**: Automatic setup and deployment
- **Three Site Generators**:
  - `sum-of-sales`: Interactive sales data visualization
  - `markdown-to-html`: Markdown to HTML converter with syntax highlighting
  - `github-user-created`: GitHub user account age checker
- **Exponential Backoff**: Reliable evaluation posting with retry logic
- **Security**: APP_SECRET verification for all requests

## Prerequisites

- Python 3.11 or higher
- GitHub Personal Access Token with repo permissions
- Environment variables configured

## Installation & Setup (macOS)

### 1. Clone/Setup Project
```bash
cd /path/to/tds-project1-dk
```

### 2. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file or export variables:
```bash
export APP_SECRET="your-secret-key"
export GITHUB_TOKEN="your-github-token"
export GITHUB_OWNER="your-github-username"
```

### 5. Run the Application
```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

The API will be available at `http://localhost:7860`

## API Endpoints

- **GET `/`**: Health check
- **GET `/health`**: Detailed health status
- **POST `/handle_task`**: Main task processing endpoint

## Request Format

```json
{
    "secret": "your-app-secret",
    "email": "your@email.com",
    "task": "task-identifier",
    "round": 1,
    "nonce": "unique-nonce",
    "evaluation_url": "https://evaluation.server/endpoint",
    "brief": "sum-of-sales",
    "attachments": {}
}
```

## Response Format

```json
{
    "status": "success",
    "repo_url": "https://github.com/owner/repo",
    "pages_url": "https://owner.github.io/repo/",
    "commit_sha": "abc123...",
    "round": 1
}
```

## Deployment on Hugging Face Spaces

### 1. Create New Space
- Go to https://huggingface.co/spaces
- Click "Create new Space"
- Choose "Custom" runtime
- Set Python version to 3.11

### 2. Upload Files
Upload these files to your Space:
- `main.py`
- `requirements.txt`
- `README.md`

### 3. Configure Space
Add to `README.md` header:
```yaml
---
title: TDS Project 1 LLM Code Deployment
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: custom
app_file: main.py
app_port: 7860
---
```

### 4. Set Environment Variables
In Space settings, add:
- `APP_SECRET`: Your secret key
- `GITHUB_TOKEN`: Your GitHub token
- `GITHUB_OWNER`: Your GitHub username

### 5. Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

## Supported Task Briefs

### sum-of-sales
- Reads CSV data and calculates total sales
- Displays interactive Bootstrap table
- Shows total in `#total-sales` element

### markdown-to-html
- Converts Markdown to HTML using marked.js
- Syntax highlighting with highlight.js
- Supports file upload and URL parameter

### github-user-created
- Fetches GitHub user creation date
- Calculates account age
- Form ID includes seed: `#github-user-{seed}`

## Testing

Test the health endpoint:
```bash
curl http://localhost:7860/health
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `APP_SECRET` | Secret key for request verification | Yes |
| `GITHUB_TOKEN` | GitHub Personal Access Token | Yes |
| `GITHUB_OWNER` | GitHub username/owner | Yes |

## Error Handling

- **401**: Invalid or missing APP_SECRET
- **400**: Invalid JSON or missing required fields
- **500**: Internal server error with JSON error details

## GitHub Permissions Required

Your GitHub token needs these scopes:
- `repo` (full repository access)
- `public_repo` (public repository access)
- `pages` (GitHub Pages management)

## Troubleshooting

### Virtual Environment Issues
```bash
deactivate
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### GitHub API Rate Limits
- Authenticated requests: 5000/hour
- Check rate limit: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit`

### Port Already in Use
```bash
lsof -ti:7860 | xargs kill
```

## Development

### Code Structure
- `main.py`: FastAPI application with all endpoints
- Helper functions for GitHub operations
- Site generators for different task types
- Exponential backoff for reliable API calls

### Adding New Site Generators
Extend the `generate_site()` function with new brief types and corresponding HTML generators.