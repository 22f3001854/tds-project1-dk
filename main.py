"""
FastAPI LLM Code Deployment Application
Handles GitHub repository creation, file uploads, and GitHub Pages setup
Uses LLM to dynamically generate HTML/JavaScript content based on task briefs
"""

import os
import json
import base64
import time
from typing import Dict, Any, Optional, List
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
from openai import OpenAI

app = FastAPI(title="TDS Project 1 - LLM Code Deployment")

# Environment variables
APP_SECRET = os.getenv("APP_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")  # AI Pipe token (replaces OPENAI_API_KEY)

if not all([APP_SECRET, GITHUB_TOKEN, GITHUB_OWNER]):
    raise RuntimeError("Missing required environment variables: APP_SECRET, GITHUB_TOKEN, GITHUB_OWNER")

# OpenAI client configured for AI Pipe (optional - will use hardcoded templates if not available)
openai_client = None
if AIPIPE_TOKEN:
    try:
        # Configure OpenAI client to use AI Pipe proxy
        openai_client = OpenAI(
            api_key=AIPIPE_TOKEN,
            base_url="https://aipipe.org/openai/v1"  # AI Pipe base URL for OpenAI models
        )
        print("✓ AI Pipe client initialized successfully - LLM generation enabled")
    except Exception as e:
        print(f"Warning: Failed to initialize AI Pipe client: {e}")
        print("Falling back to hardcoded templates.")
        openai_client = None
else:
    print("Warning: AIPIPE_TOKEN not set. Using hardcoded templates instead of LLM generation.")

GITHUB_API_BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "tds-project1-dk"
}

# Pydantic models for request validation
class Attachment(BaseModel):
    """Attachment data model"""
    name: str = Field(..., description="Attachment filename")
    url: str = Field(..., description="Data URL or HTTP URL to attachment content")

class TaskRequest(BaseModel):
    """Request model for /handle_task endpoint"""
    email: str = Field(..., description="User email address")
    secret: str = Field(..., description="Shared secret for authentication")
    task: str = Field(..., description="Task identifier (e.g., 'sum-of-sales-001')")
    round: int = Field(..., description="Round number (1 or 2)", ge=1, le=2)
    nonce: str = Field(..., description="Unique nonce for this request")
    brief: str = Field(..., description="Task description/brief (e.g., 'sum-of-sales', 'markdown-to-html')")
    evaluation_url: str = Field(..., description="URL to POST evaluation results")
    attachments: Optional[List[Attachment]] = Field(default=[], description="Optional list of attachments")

def create_or_get_repo(name: str) -> Dict[str, Any]:
    """
    Create a new public GitHub repository or get existing one.
    
    Args:
        name: Repository name
        
    Returns:
        Repository data from GitHub API
    """
    # Check if repo exists first
    check_url = f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{name}"
    response = requests.get(check_url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()
    
    # Create new repository
    create_url = f"{GITHUB_API_BASE}/user/repos"
    repo_data = {
        "name": name,
        "description": f"TDS Project 1 - {name}",
        "public": True,
        "auto_init": False
    }
    
    response = requests.post(create_url, headers=HEADERS, json=repo_data)
    if response.status_code not in [200, 201]:
        raise HTTPException(status_code=500, detail=f"Failed to create repository: {response.text}")
    
    return response.json()

def enable_pages(name: str) -> Dict[str, Any]:
    """
    Enable GitHub Pages for the repository.
    
    Args:
        name: Repository name
        
    Returns:
        Pages configuration data
    """
    pages_url = f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{name}/pages"
    pages_data = {
        "source": {
            "branch": "main",
            "path": "/"
        }
    }
    
    response = requests.post(pages_url, headers=HEADERS, json=pages_data)
    if response.status_code not in [200, 201, 409]:  # 409 = already exists
        raise HTTPException(status_code=500, detail=f"Failed to enable pages: {response.text}")
    
    if response.status_code == 409:
        # Pages already enabled, get current config
        response = requests.get(pages_url, headers=HEADERS)
    
    return response.json() if response.status_code in [200, 201] else {"status": "already_enabled"}

def put_file(name: str, path: str, content_bytes: bytes, message: str) -> Dict[str, Any]:
    """
    Upload or update a file in the GitHub repository.
    
    Args:
        name: Repository name
        path: File path in repository
        content_bytes: File content as bytes
        message: Commit message
        
    Returns:
        Commit data from GitHub API
    """
    file_url = f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{name}/contents/{path}"
    
    # Check if file exists to get SHA
    existing_response = requests.get(file_url, headers=HEADERS)
    sha = None
    if existing_response.status_code == 200:
        sha = existing_response.json().get("sha")
    
    # Prepare file data
    file_data = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8")
    }
    
    if sha:
        file_data["sha"] = sha
    
    response = requests.put(file_url, headers=HEADERS, json=file_data)
    if response.status_code not in [200, 201]:
        raise HTTPException(status_code=500, detail=f"Failed to upload file {path}: {response.text}")
    
    return response.json()

def generate_content_with_llm(task: str, brief: str, task_type: str) -> str:
    """
    Use LLM to generate HTML/JavaScript content dynamically based on the brief.
    
    Args:
        task: Task identifier
        brief: Task description/brief
        task_type: Type of task (sum-of-sales, markdown-to-html, github-user-created)
        
    Returns:
        Generated HTML content as string
    """
    if not openai_client:
        # Fallback to hardcoded templates if no LLM available
        return None
    
    # Construct LLM prompt based on task type
    if "sum-of-sales" in task_type:
        prompt = f"""Generate a complete, self-contained HTML file for a sales summary application.

Requirements:
- Title: "Sales Summary"
- Use Bootstrap 5 CDN for styling
- Display total sales in an element with id="total-sales"
- Show a Bootstrap table with sales data
- Include JavaScript that:
  1. Fetches data from 'data.csv' file
  2. Parses the CSV (format: item,sales)
  3. Calculates total sales and displays in #total-sales
  4. Renders all items in a Bootstrap table

Additional requirements from brief: {brief}

Return ONLY the complete HTML file (<!DOCTYPE html> through </html>). No explanations."""

    elif "markdown" in task_type:
        prompt = f"""Generate a complete, self-contained HTML file for a Markdown to HTML converter.

Requirements:
- Title: "Markdown to HTML Converter"
- Use Bootstrap 5 CDN for styling
- Include marked.js CDN for markdown parsing
- Include highlight.js CDN for syntax highlighting
- Load and render 'input.md' file or accept ?url parameter
- Display rendered HTML in a container

Additional requirements from brief: {brief}

Return ONLY the complete HTML file. No explanations."""

    elif "github-user" in task_type:
        # Extract seed from task name if present
        seed = task.split('-')[-1] if '-' in task else "default"
        prompt = f"""Generate a complete, self-contained HTML file for a GitHub user account age checker.

Requirements:
- Title: "GitHub User Account Age"
- Use Bootstrap 5 CDN for styling
- Include a form with id="github-user-{seed}"
- Form should have an input for GitHub username and submit button
- On submit, fetch user data from GitHub API: https://api.github.com/users/{{username}}
- Display account creation date from 'created_at' field
- Calculate and display account age in years and days
- Show results in Bootstrap alert

Additional requirements from brief: {brief}

Return ONLY the complete HTML file. No explanations."""

    else:
        prompt = f"""Generate a complete, self-contained HTML file based on this brief:

{brief}

Task: {task}

Requirements:
- Use Bootstrap 5 CDN for styling
- Include all necessary JavaScript inline
- Make it fully functional and self-contained
- Follow best practices for HTML5

Return ONLY the complete HTML file. No explanations."""

    try:
        response = openai_client.chat.completions.create(
            model="openai/gpt-4o-mini",  # AI Pipe format: prefix with 'openai/'
            messages=[
                {"role": "system", "content": "You are an expert web developer. Generate complete, working HTML files with embedded JavaScript. Return only the HTML code, no explanations or markdown code blocks."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        html_content = response.choices[0].message.content.strip()
        
        # Remove markdown code fences if present
        if html_content.startswith("```"):
            lines = html_content.split('\n')
            html_content = '\n'.join(lines[1:-1]) if len(lines) > 2 else html_content
        
        return html_content
        
    except Exception as e:
        print(f"LLM generation failed: {e}. Falling back to templates.")
        return None

def generate_site(task: str, brief: str, round_num: int, attachments: Optional[Dict] = None) -> Dict[str, bytes]:
    """
    Generate static site files based on task brief.
    
    Args:
        task: Task identifier
        brief: Task description/brief
        round_num: Round number (1 or 2)
        attachments: Optional attachments data
        
    Returns:
        Dictionary mapping filenames to file content as bytes
    """
    files = {}
    
    # Determine task type from task identifier or brief
    task_lower = task.lower()
    brief_lower = brief.lower()
    
    # Try LLM generation first
    task_type = ""
    if "sum-of-sales" in task_lower or "sum-of-sales" in brief_lower:
        task_type = "sum-of-sales"
    elif "markdown-to-html" in task_lower or "markdown-to-html" in brief_lower or "markdown" in task_lower:
        task_type = "markdown-to-html"
    elif "github-user" in task_lower or "github-user" in brief_lower:
        task_type = "github-user-created"
    
    # Generate HTML using LLM (if available) or fallback to templates
    html_content = None
    if openai_client and task_type:
        html_content = generate_content_with_llm(task, brief, task_type)
    
    # If LLM generation failed or not available, use hardcoded templates
    if not html_content:
        if task_type == "sum-of-sales":
            # Generate sum-of-sales HTML
            html_content = generate_sum_of_sales_html()
    
    # Set HTML content for all task types
    if html_content:
        files["index.html"] = html_content.encode("utf-8")
    
    # Add task-specific data files
    if task_type == "sum-of-sales":
        csv_content = """item,sales
Product A,1500
Product B,2300
Product C,800
Product D,1200
Product E,900"""
        files["data.csv"] = csv_content.encode("utf-8")
        
    elif task_type == "markdown-to-html":
        # If no HTML from LLM, use template
        if not html_content:
            html_content = generate_markdown_to_html()
            files["index.html"] = html_content.encode("utf-8")
        
        # Sample markdown file
        md_content = """# Sample Markdown
This is a **sample** markdown file with:
- Lists
- *Italic text*
- `Code blocks`

## Code Example
```python
def hello_world():
    print("Hello, World!")
```"""
        files["input.md"] = md_content.encode("utf-8")
        
    elif task_type == "github-user-created":
        # If no HTML from LLM, use template
        if not html_content:
            html_content = generate_github_user_created_html(task)
            files["index.html"] = html_content.encode("utf-8")
    
    # Always add README and LICENSE
    files["README.md"] = generate_readme(task, brief, round_num).encode("utf-8")
    files["LICENSE"] = generate_license().encode("utf-8")
    
    return files

def generate_sum_of_sales_html() -> str:
    """Generate HTML for sum-of-sales task."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sales Summary</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1>Sales Summary</h1>
        <div class="alert alert-info">
            <h4>Total Sales: $<span id="total-sales">0</span></h4>
        </div>
        <table class="table table-striped" id="sales-table">
            <thead>
                <tr>
                    <th>Item</th>
                    <th>Sales</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>
    
    <script>
        async function loadSalesData() {
            try {
                const response = await fetch('data.csv');
                const csvText = await response.text();
                const lines = csvText.trim().split('\\n');
                const headers = lines[0].split(',');
                
                let totalSales = 0;
                const tableBody = document.querySelector('#sales-table tbody');
                
                for (let i = 1; i < lines.length; i++) {
                    const row = lines[i].split(',');
                    const item = row[0];
                    const sales = parseFloat(row[1]);
                    
                    totalSales += sales;
                    
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td>${item}</td><td>$${sales}</td>`;
                    tableBody.appendChild(tr);
                }
                
                document.getElementById('total-sales').textContent = totalSales.toFixed(2);
            } catch (error) {
                console.error('Error loading sales data:', error);
            }
        }
        
        loadSalesData();
    </script>
</body>
</html>"""

def generate_markdown_to_html() -> str:
    """Generate HTML for markdown-to-html converter."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Markdown to HTML Converter</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.3.1/styles/default.min.css">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.3.1/highlight.min.js"></script>
</head>
<body>
    <div class="container mt-5">
        <h1>Markdown to HTML Converter</h1>
        <div class="row">
            <div class="col-md-6">
                <h3>Markdown Input</h3>
                <textarea id="markdown-input" class="form-control" rows="15" placeholder="Enter markdown here..."></textarea>
                <button class="btn btn-primary mt-2" onclick="convertMarkdown()">Convert</button>
                <button class="btn btn-secondary mt-2" onclick="loadFromFile()">Load from input.md</button>
            </div>
            <div class="col-md-6">
                <h3>HTML Output</h3>
                <div id="html-output" class="border p-3" style="min-height: 400px; background-color: #f8f9fa;"></div>
            </div>
        </div>
    </div>
    
    <script>
        function convertMarkdown() {
            const markdownText = document.getElementById('markdown-input').value;
            const htmlOutput = marked.parse(markdownText);
            document.getElementById('html-output').innerHTML = htmlOutput;
            hljs.highlightAll();
        }
        
        async function loadFromFile() {
            try {
                const response = await fetch('input.md');
                const markdownText = await response.text();
                document.getElementById('markdown-input').value = markdownText;
                convertMarkdown();
            } catch (error) {
                console.error('Error loading markdown file:', error);
                alert('Could not load input.md file');
            }
        }
        
        // Check for URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        const urlParam = urlParams.get('url');
        if (urlParam) {
            fetch(urlParam)
                .then(response => response.text())
                .then(text => {
                    document.getElementById('markdown-input').value = text;
                    convertMarkdown();
                })
                .catch(error => console.error('Error loading from URL:', error));
        } else {
            loadFromFile();
        }
    </script>
</body>
</html>"""

def generate_github_user_created_html(task: str) -> str:
    """Generate HTML for GitHub user creation date checker."""
    # Extract seed from task if present
    seed = "123"  # default
    if "seed" in task:
        import re
        seed_match = re.search(r'seed[=:]?(\d+)', task)
        if seed_match:
            seed = seed_match.group(1)
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub User Creation Date</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1>GitHub User Creation Date Checker</h1>
        <form id="github-user-{seed}" class="mb-4">
            <div class="mb-3">
                <label for="username" class="form-label">GitHub Username</label>
                <input type="text" class="form-control" id="username" placeholder="Enter GitHub username" required>
            </div>
            <button type="submit" class="btn btn-primary">Check User</button>
        </form>
        
        <div id="result" class="alert" style="display: none;"></div>
        <div id="user-info" style="display: none;">
            <h3>User Information</h3>
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title" id="user-name"></h5>
                    <p class="card-text">
                        <strong>Created:</strong> <span id="created-date"></span><br>
                        <strong>Account Age:</strong> <span id="account-age"></span><br>
                        <strong>Public Repos:</strong> <span id="public-repos"></span><br>
                        <strong>Followers:</strong> <span id="followers"></span>
                    </p>
                    <img id="avatar" class="rounded-circle" width="100" height="100">
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('github-user-{seed}').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            const username = document.getElementById('username').value.trim();
            const resultDiv = document.getElementById('result');
            const userInfoDiv = document.getElementById('user-info');
            
            if (!username) {{
                showResult('Please enter a username', 'danger');
                return;
            }}
            
            try {{
                const response = await fetch(`https://api.github.com/users/${{username}}`);
                
                if (!response.ok) {{
                    if (response.status === 404) {{
                        showResult('User not found', 'warning');
                    }} else {{
                        showResult('Error fetching user data', 'danger');
                    }}
                    userInfoDiv.style.display = 'none';
                    return;
                }}
                
                const userData = await response.json();
                
                // Calculate account age
                const createdDate = new Date(userData.created_at);
                const now = new Date();
                const ageInDays = Math.floor((now - createdDate) / (1000 * 60 * 60 * 24));
                const ageInYears = Math.floor(ageInDays / 365);
                const remainingDays = ageInDays % 365;
                
                // Display user information
                document.getElementById('user-name').textContent = userData.name || userData.login;
                document.getElementById('created-date').textContent = createdDate.toLocaleDateString();
                document.getElementById('account-age').textContent = `${{ageInYears}} years, ${{remainingDays}} days`;
                document.getElementById('public-repos').textContent = userData.public_repos;
                document.getElementById('followers').textContent = userData.followers;
                document.getElementById('avatar').src = userData.avatar_url;
                
                showResult('User found successfully!', 'success');
                userInfoDiv.style.display = 'block';
                
            }} catch (error) {{
                console.error('Error:', error);
                showResult('Network error occurred', 'danger');
                userInfoDiv.style.display = 'none';
            }}
        }});
        
        function showResult(message, type) {{
            const resultDiv = document.getElementById('result');
            resultDiv.className = `alert alert-${{type}}`;
            resultDiv.textContent = message;
            resultDiv.style.display = 'block';
        }}
    </script>
</body>
</html>"""

def generate_readme(task: str, brief: str, round_num: int) -> str:
    """Generate README.md content."""
    return f"""# TDS Project 1 - {task}

## Description
This project implements a {brief} application as part of TDS Project 1, Round {round_num}.

## Features
- Static HTML/JavaScript implementation
- Bootstrap 5 for styling
- Responsive design
- GitHub Pages deployment

## Usage
Simply open `index.html` in a web browser or visit the GitHub Pages URL.

## Generated on
{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}

## Task Details
- Task: {task}
- Brief: {brief}
- Round: {round_num}
"""

def generate_license() -> str:
    """Generate MIT license content."""
    return f"""MIT License

Copyright (c) {time.strftime('%Y')} TDS Project 1

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

def post_evaluation_with_backoff(url: str, data: Dict[str, Any], max_retries: int = 5) -> bool:
    """
    Post evaluation data with exponential backoff.
    
    Args:
        url: Evaluation URL
        data: Data to post
        max_retries: Maximum number of retry attempts
        
    Returns:
        True if successful, False otherwise
    """
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=data, timeout=30)
            if response.status_code in [200, 201]:
                return True
            
            print(f"Evaluation post attempt {attempt + 1} failed: {response.status_code}")
            
        except requests.RequestException as e:
            print(f"Evaluation post attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:
            wait_time = min(2 ** attempt, 16)  # Exponential backoff, max 16s
            time.sleep(wait_time)
    
    return False

@app.post("/handle_task")
async def handle_task(payload: TaskRequest):
    """
    Main endpoint to handle TDS server requests.
    
    Processes both Round 1 and Round 2 tasks:
    - Verifies APP_SECRET
    - Creates/updates GitHub repository
    - Generates and uploads files
    - Enables GitHub Pages
    - Posts evaluation response
    """
    try:
        # Verify secret
        if payload.secret != APP_SECRET:
            raise HTTPException(status_code=401, detail="Invalid secret")
        
        # Extract task data
        email = payload.email
        task = payload.task
        round_num = payload.round
        nonce = payload.nonce
        evaluation_url = payload.evaluation_url
        brief = payload.brief
        attachments = payload.attachments or []
        
        # Generate repository name
        repo_name = f"tds-project1-{task}"
        
        # Create or get repository
        repo_data = create_or_get_repo(repo_name)
        repo_url = repo_data["html_url"]
        
        # Generate site files
        files = generate_site(task, brief, round_num, attachments)
        
        # Upload files
        latest_commit_sha = None
        for filename, content in files.items():
            commit_data = put_file(repo_name, filename, content, f"Round {round_num}: Add {filename}")
            latest_commit_sha = commit_data["commit"]["sha"]
        
        # Enable GitHub Pages (only needed for Round 1, but safe to call multiple times)
        enable_pages(repo_name)
        
        # Construct Pages URL
        pages_url = f"https://{GITHUB_OWNER}.github.io/{repo_name}/"
        
        # Prepare evaluation response
        evaluation_data = {
            "email": email,
            "task": task,
            "round": round_num,
            "nonce": nonce,
            "repo_url": repo_url,
            "commit_sha": latest_commit_sha,
            "pages_url": pages_url
        }
        
        # Post evaluation with backoff
        success = post_evaluation_with_backoff(evaluation_url, evaluation_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to post evaluation after multiple attempts")
        
        return JSONResponse(content={
            "status": "success",
            "repo_url": repo_url,
            "pages_url": pages_url,
            "commit_sha": latest_commit_sha,
            "round": round_num
        })
        
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"Internal server error: {str(e)}"
        return JSONResponse(
            status_code=500,
            content={"error": error_detail}
        )

@app.get("/")
async def root():
    """API documentation landing page."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TDS Project 1 - LLM Code Deployment API</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1>🚀 TDS Project 1 - LLM Code Deployment API</h1>
            <p class="lead">FastAPI application for automated GitHub repository creation and deployment</p>
            
            <div class="alert alert-success">
                <strong>Status:</strong> Running ✅
            </div>
            
            <h2>📡 Endpoints</h2>
            <ul class="list-group mb-4">
                <li class="list-group-item">
                    <strong>POST /handle_task</strong> - Main endpoint for handling deployment tasks
                </li>
                <li class="list-group-item">
                    <strong>GET /health</strong> - Health check endpoint
                </li>
                <li class="list-group-item">
                    <strong>GET /docs</strong> - Interactive API documentation (Swagger UI)
                </li>
                <li class="list-group-item">
                    <strong>GET /redoc</strong> - Alternative API documentation (ReDoc)
                </li>
            </ul>
            
            <h2>🔧 Usage</h2>
            <p>Send a POST request to <code>/handle_task</code> with the following JSON payload:</p>
            <pre class="bg-light p-3"><code>{
  "email": "your-email@example.com",
  "secret": "your-app-secret",
  "task": "task-name",
  "round": 1,
  "nonce": "unique-nonce",
  "brief": "task description",
  "evaluation_url": "https://evaluation-endpoint.com",
  "attachments": []
}</code></pre>
            
            <h2>📚 Documentation</h2>
            <div class="btn-group mb-4" role="group">
                <a href="/docs" class="btn btn-primary">Swagger UI</a>
                <a href="/redoc" class="btn btn-secondary">ReDoc</a>
                <a href="/health" class="btn btn-info">Health Check</a>
            </div>
            
            <h2>✨ Supported Tasks</h2>
            <ul>
                <li><strong>sum-of-sales</strong> - Generate sales summary with Bootstrap table</li>
                <li><strong>markdown-to-html</strong> - Markdown renderer with syntax highlighting</li>
                <li><strong>github-user-created</strong> - GitHub user account creation date checker</li>
            </ul>
            
            <footer class="mt-5 text-muted">
                <p>TDS Project 1 | FastAPI + GitHub API | 2025</p>
            </footer>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "github_owner": GITHUB_OWNER,
        "has_github_token": bool(GITHUB_TOKEN),
        "has_app_secret": bool(APP_SECRET)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
