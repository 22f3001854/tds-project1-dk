# Hugging Face Spaces Deployment Guide

## Environment Variables Setup

For the application to work on Hugging Face Spaces, you need to configure the following **Secrets** in your Space settings:

### Required Secrets

1. **APP_SECRET** - Your application secret key for authentication
   - Go to your HF Space → Settings → Variables and secrets
   - Add new secret: Name: `APP_SECRET`, Value: `your-secret-key`

2. **GITHUB_TOKEN** - GitHub Personal Access Token with repo permissions
   - Name: `GITHUB_TOKEN`
   - Value: Your GitHub token (starts with `ghp_` or `github_pat_`)

3. **GITHUB_OWNER** - Your GitHub username
   - Name: `GITHUB_OWNER`
   - Value: `22f3001854`

### Optional Secrets

4. **OPENAI_API_KEY** - OpenAI API key for LLM-based content generation
   - Name: `OPENAI_API_KEY`
   - Value: Your OpenAI API key (starts with `sk-`)
   - **Note**: If not provided, the app will use hardcoded HTML templates

## Deployment Steps

1. **Push to GitHub** (already done ✓)

2. **Create/Update HF Space**
   - The space will automatically sync from GitHub repository
   - Space URL: https://huggingface.co/spaces/22f3001854/tds-project1-dk

3. **Configure Secrets**
   - Go to: https://huggingface.co/spaces/22f3001854/tds-project1-dk/settings
   - Click on "Variables and secrets" tab
   - Add all required secrets listed above

4. **Verify Deployment**
   - Check the Build logs for any errors
   - Test the health endpoint: `https://22f3001854-tds-project1-dk.hf.space/health`
   - Test the API with a POST request to `/handle_task`

## Current Space Status

- Repository: Linked to `https://github.com/22f3001854/tds-project1-dk`
- Runtime: Python 3.14
- Port: 7860
- Status: Active at https://22f3001854-tds-project1-dk.hf.space

## Troubleshooting

### OpenAI Client Issues
If you see warnings about Pydantic V1 compatibility, this is expected with Python 3.14. The app will still work correctly.

### LLM Generation Not Working
- Verify `OPENAI_API_KEY` is set correctly in HF Secrets
- Check the app logs - it should show "✓ OpenAI client initialized successfully"
- If the key is invalid, the app will fall back to hardcoded templates

### Missing Environment Variables
If the app fails to start with "Missing required environment variables", ensure all **Required Secrets** are configured in HF Space settings.
