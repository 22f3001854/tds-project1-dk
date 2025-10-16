# AI Pipe Setup Guide

## What is AI Pipe?

AI Pipe is a proxy service that provides unified access to multiple LLM providers (OpenAI, Anthropic, Google, etc.) through a single API interface. It's cost-effective and OpenAI-compatible.

## Getting Your AI Pipe Token

### Step 1: Visit AI Pipe Website
Go to: **https://aipipe.org**

### Step 2: Sign Up / Login
- Create an account if you don't have one
- Login with your IIT credentials if required

### Step 3: Get Your Token
- Navigate to the API section or Dashboard
- Find your **AI Pipe Token** (or API Key)
- Copy the token - it should look something like: `aipipe_xxxxxxxxxx`

### Step 4: Configure Environment Variables

#### For Local Development:
Add to your `.env` file:
```bash
export AIPIPE_TOKEN="your-aipipe-token-here"
```

Then restart your server:
```bash
./start_server.sh
```

#### For Hugging Face Spaces:
1. Go to: https://huggingface.co/spaces/22f3001854/tds-project1-dk/settings
2. Click "Variables and secrets" tab
3. Add new secret:
   - **Name**: `AIPIPE_TOKEN`
   - **Value**: Your AI Pipe token
4. Save and wait for the space to rebuild

## How AI Pipe Works in This Project

```python
# Configuration in main.py
openai_client = OpenAI(
    api_key=AIPIPE_TOKEN,                    # Your AI Pipe token
    base_url="https://aipipe.org/openai/v1"  # AI Pipe proxy URL
)

# Model name for AI Pipe
model = "gpt-4.1-nano"  # Fast and cost-efficient model
```

**Note**: AI Pipe uses `gpt-4.1-nano` which is optimized for speed and cost-efficiency.

## Available Models via AI Pipe

The application uses **gpt-4.1-nano** which is:
- ✅ Fast response times
- ✅ Cost-efficient
- ✅ Optimized for code generation
- ✅ Available through AI Pipe

Other models you could try (update in `main.py` line 253):
- `gpt-4.1-nano` (current - recommended)
- `gpt-3.5-turbo`
- Check AI Pipe documentation for more options

## Benefits

✅ **Cost-Effective**: Often cheaper than direct API access  
✅ **Unified Interface**: Same code works for multiple providers  
✅ **IIT Approved**: Required for TDS course projects  
✅ **Simple Migration**: OpenAI-compatible API  
✅ **No Quota Issues**: Better rate limits than free OpenAI tier  

## Testing

After configuring your token, test it:

```bash
# Local
curl -X POST http://127.0.0.1:7860/handle_task \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "test@example.com",
    "secret": "YaarThachaSattaiThathaThachaSattai",
    "task": "test-aipipe",
    "round": 1,
    "nonce": "test-001",
    "brief": "Create a colorful sales dashboard",
    "evaluation_url": "https://httpbin.org/post",
    "attachments": [{"name": "data.csv", "url": "data:text/csv;base64,cHJvZHVjdCxzYWxlcwpBLDEwMAo="}]
  }'
```

Check the server logs for:
```
✓ AI Pipe client initialized successfully - LLM generation enabled
```

## Troubleshooting

### "AIPIPE_TOKEN not set"
- Make sure you exported the variable in your `.env` file
- Restart the server after adding the token

### "Failed to initialize AI Pipe client"
- Verify your token is correct (no extra spaces)
- Check if you have access to AI Pipe
- Try generating a new token

### "Rate limit exceeded"
- AI Pipe has usage limits per token
- Check your AI Pipe dashboard for limits
- Contact AI Pipe support if needed

### LLM still using fallback templates
- Check server logs for error messages
- Verify the base_url is exactly: `https://aipipe.org/openai/v1`
- Ensure model name has correct prefix: `openai/gpt-4o-mini`

## Documentation

- **AI Pipe Docs**: https://aipipe.org/docs
- **API Reference**: https://aipipe.org/api
- **IIT TDS Course**: Check your course materials for AI Pipe access

## Support

If you have issues:
1. Check AI Pipe documentation
2. Verify your token hasn't expired
3. Contact your course instructor for IIT-specific help
4. Check the app logs for detailed error messages
