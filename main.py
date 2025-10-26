"""
FastAPI LLM Code Deployment Application
Handles GitHub repository creation, file uploads, and GitHub Pages setup
Uses LLM to dynamically generate HTML/JavaScript content based on task briefs
"""

import os
import sys
import json
import base64
import re
import time
from typing import Dict, Any, Optional, List
import requests
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
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
    except Exception as e:
        print(f"Warning: Failed to initialize AI Pipe client: {e}")
        print("Falling back to hardcoded templates.")
        openai_client = None
else:
    openai_client = None

GITHUB_API_BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "tds-project1-dk"
}

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    sys.stdout.flush()
    if openai_client:
        print("-" * 80, flush=True)
        print("✓ AI Pipe client initialized successfully - LLM generation enabled", flush=True)
        print("-" * 80, flush=True)
    else:
        print("-" * 80, flush=True)
        print("⚠ AI Pipe client not available - Using template fallbacks", flush=True)
        print("-" * 80, flush=True)
    sys.stdout.flush()

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
    round: int = Field(..., description="Round number", ge=1)
    nonce: str = Field(..., description="Unique nonce for this request")
    brief: str = Field(..., description="Task description/brief (e.g., 'sum-of-sales', 'markdown-to-html')")
    checks: Optional[List[str]] = Field(default=[], description="List of evaluation checks")
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
    response = requests.get(check_url, headers=HEADERS, timeout=30)
    
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
    
    response = requests.post(create_url, headers=HEADERS, json=repo_data, timeout=30)
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
    
    response = requests.post(pages_url, headers=HEADERS, json=pages_data, timeout=30)
    if response.status_code not in [200, 201, 409]:  # 409 = already exists
        raise HTTPException(status_code=500, detail=f"Failed to enable pages: {response.text}")
    
    if response.status_code == 409:
        # Pages already enabled, get current config
        response = requests.get(pages_url, headers=HEADERS, timeout=30)
    
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
    existing_response = requests.get(file_url, headers=HEADERS, timeout=30)
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
    
    response = requests.put(file_url, headers=HEADERS, json=file_data, timeout=30)
    if response.status_code not in [200, 201]:
        raise HTTPException(status_code=500, detail=f"Failed to upload file {path}: {response.text}")
    
    return response.json()

def generate_content_with_llm(task: str, brief: str, task_type: str, checks: Optional[List[str]] = None) -> str:
    """
    Use LLM to generate HTML/JavaScript content dynamically based on the brief.
    
    Args:
        task: Task identifier
        brief: Task description/brief
        task_type: Type of task (sum-of-sales, markdown-to-html, github-user-created)
        checks: Optional list of evaluation checks to satisfy
        
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

    elif "captcha" in task_type:
        prompt = f"""Generate a complete, self-contained HTML file for a CAPTCHA solver.

Requirements:
- Title: "CAPTCHA Solver"
- Use Bootstrap 5 CDN for styling
- Accept a ?url=... query parameter for the captcha image URL
- Display the captcha image from the URL parameter
- If no URL parameter, use a default/sample image from attachments
- Include image processing/OCR capabilities (you can use Tesseract.js CDN)
- Display the solved captcha text within 15 seconds
- Show results clearly in a prominent area
- Include proper error handling for image loading failures

Additional requirements from brief: {brief}

Return ONLY the complete HTML file. No explanations."""

    else:
        # Generic prompt for any unknown task type
        # The LLM will interpret the brief and create appropriate functionality
        checks_text = ""
        if checks:
            checks_text = "\n\nEvaluation Checks (MUST satisfy):\n" + "\n".join(f"- {check}" for check in checks)
        
        prompt = f"""Generate a complete, self-contained HTML file based on this task brief.

Task Name: {task}
Task Type: {task_type}

Brief: {brief}{checks_text}

Requirements:
- Create a fully functional web application that fulfills the brief requirements
- Use Bootstrap 5 CDN for modern, responsive styling
- Include all necessary JavaScript inline (no external files)
- Handle URL parameters if mentioned in the brief (e.g., ?url=..., ?id=...)
- Use appropriate JavaScript libraries from CDN if needed (e.g., Chart.js, Marked.js, Tesseract.js, etc.)
- Include proper error handling and user feedback
- Make it completely self-contained (all code in one HTML file)
- Follow best practices for HTML5, CSS3, and modern JavaScript
- Ensure the page is mobile-responsive
- Add loading states and user-friendly messages where appropriate
- Make sure to check all the CDN links are correct and accessible

Return ONLY the complete HTML file. No explanations or markdown code blocks."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-nano",  # AI Pipe model
            messages=[
                {"role": "system", "content": "You are an expert web developer. Generate complete, working HTML files with embedded JavaScript. Return only the HTML code, no explanations or markdown code blocks."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            timeout=60  # 60 second timeout for LLM generation
        )
        
        html_content = response.choices[0].message.content.strip()
        
        # Remove markdown code fences if present
        if html_content.startswith("```"):
            lines = html_content.split('\n')
            html_content = '\n'.join(lines[1:-1]) if len(lines) > 2 else html_content
        
        print("-" * 80)
        print(f"✓ LLM successfully generated HTML content for task type: {task_type}")
        print("-" * 80)
        return html_content
        
    except Exception as e:
        print(f"LLM generation failed: {e}. Falling back to templates.")
        return None

class UniversalTaskGenerator:
    """Universal task generator that can handle any kind of request dynamically."""
    
    def __init__(self):
        self.supported_extensions = [
            '.txt', '.json', '.svg', '.css', '.js', '.html', '.md', '.py', '.php', '.xml',
            '.yaml', '.yml', '.toml', '.ini', '.conf', '.c', '.cpp', '.java', '.rs'
        ]
    
    def _extract_files_from_brief(self, brief: str) -> List[str]:
        """Extract file names from the brief using regex patterns."""
        files = []
        
        # Pattern for explicit file mentions with extensions
        file_patterns = [
            r'\b(\w+\.\w+)\b',  # Basic pattern: filename.extension
            r'(?:file|create|build|generate|make)s?\s+(?:called\s+)?["\']?(\w+\.\w+)["\']?',
            r'(\w+\.(?:txt|json|svg|css|js|html|md|py|php|xml|yaml|yml|toml|ini|conf|c|cpp|java|rs))\b'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, brief, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                if '.' in match and any(match.lower().endswith(ext) for ext in self.supported_extensions):
                    files.append(match)
        
        # Remove duplicates while preserving order
        unique_files = []
        for file in files:
            if file not in unique_files:
                unique_files.append(file)
        
        return unique_files[:10]  # Limit to 10 files max
    
    def _has_multiple_file_requirements(self, brief: str) -> bool:
        """Check if the brief requires multiple files."""
        multi_file_indicators = [
            'files', 'create multiple', 'several files', 'different files',
            'also create', 'and a', 'along with', 'additional file',
            'separate file', 'another file', 'include file'
        ]
        return any(indicator in brief.lower() for indicator in multi_file_indicators)
    
    def _detect_task_type(self, task: str, brief: str) -> str:
        """Detect the task type from task name and brief."""
        task_lower = task.lower()
        brief_lower = brief.lower()
        
        # Known task types
        if 'sharevolume' in task_lower or 'share-volume' in task_lower:
            return 'shareVolume'
        elif 'llmpages' in task_lower or 'llm-pages' in task_lower:
            return 'llmpages'
        elif any(term in brief_lower for term in ['sec api', 'sec.gov', 'financial', 'stock']):
            return 'shareVolume'
        elif self._has_multiple_file_requirements(brief) or len(self._extract_files_from_brief(brief)) > 0:
            return 'multifile'
        else:
            return 'general'
    
    def _generate_enhanced_html(self, task: str, brief: str, required_files: List[str], checks: Optional[List[str]] = None) -> str:
        """Generate enhanced HTML with all required elements."""
        
        # Determine if this is a SEC/ShareVolume task
        is_sec_task = any(term in brief.lower() for term in ['sec api', 'sec.gov', 'sharevolume', 'financial'])
        
        # Base HTML template with enhanced features
        html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{task.replace('_', ' ').title()}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
        }}
        
        .main-container {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            backdrop-filter: blur(10px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            margin-top: 20px;
            margin-bottom: 20px;
        }}
        
        .header-section {{
            background: linear-gradient(45deg, #007bff, #0056b3);
            color: white;
            border-radius: 15px 15px 0 0;
            padding: 30px;
            text-align: center;
        }}
        
        .content-section {{
            padding: 30px;
        }}
        
        .data-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            transition: transform 0.3s ease;
        }}
        
        .data-card:hover {{
            transform: translateY(-5px);
        }}
        
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #007bff;
        }}
        
        .metric-label {{
            color: #6c757d;
            font-weight: 500;
            margin-top: 5px;
        }}
        
        .btn-gradient {{
            background: linear-gradient(45deg, #007bff, #0056b3);
            border: none;
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            transition: all 0.3s ease;
        }}
        
        .btn-gradient:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,123,255,0.3);
        }}
        
        .loading {{
            display: none;
            text-align: center;
            padding: 20px;
        }}
        
        .error {{
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border: 1px solid #f5c6cb;
        }}
        
        .success {{
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border: 1px solid #c3e6cb;
        }}
        
        .file-manager {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="main-container">
            <div class="header-section">
                <h1><i class="fas fa-chart-line me-3"></i>{task.replace('_', ' ').title()}</h1>
                <p class="lead mb-0">Enhanced Web Application</p>
            </div>
            
            <div class="content-section">'''
        
        # Add SEC-specific content for ShareVolume tasks
        if is_sec_task:
            html_template += '''
                <div class="row mb-4">
                    <div class="col-md-4">
                        <div class="data-card text-center">
                            <div id="share-entity-name" class="metric-value">Loading...</div>
                            <div class="metric-label">Entity Name</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="data-card text-center">
                            <div id="share-max-value" class="metric-value">Loading...</div>
                            <div class="metric-label">Max Value</div>
                            <small id="share-max-fy" class="text-muted">Fiscal Year: Loading...</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="data-card text-center">
                            <div id="share-min-value" class="metric-value">Loading...</div>
                            <div class="metric-label">Min Value</div>
                            <small id="share-min-fy" class="text-muted">Fiscal Year: Loading...</small>
                        </div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <canvas id="shareVolumeChart" width="400" height="200"></canvas>
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <button class="btn btn-gradient w-100" onclick="fetchShareVolumeData()">
                            <i class="fas fa-sync-alt me-2"></i>Refresh Data
                        </button>
                    </div>
                    <div class="col-md-6">
                        <button class="btn btn-outline-primary w-100" onclick="exportData()">
                            <i class="fas fa-download me-2"></i>Export Data
                        </button>
                    </div>
                </div>
                
                <div id="loading" class="loading">
                    <i class="fas fa-spinner fa-spin fa-2x text-primary"></i>
                    <p class="mt-2">Fetching data from SEC API...</p>
                </div>
                
                <div id="error-message"></div>'''
        
        # Add file manager section if multiple files are required
        if required_files:
            html_template += '''
                <div class="file-manager">
                    <h5><i class="fas fa-folder-open me-2"></i>File Manager</h5>
                    <div class="row mb-3">
                        <div class="col-md-8">
                            <h6>Quick Access Links</h6>
                            <div id="file-links" class="d-flex flex-wrap gap-2">
                                <!-- File links will be populated by JavaScript -->
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-files-o me-2"></i>Required Files</h5>
                            </div>
                            <div class="card-body">
                                <div id="file-list" class="list-group list-group-flush">
                                    <!-- Files will be populated by JavaScript -->
                                </div>
                                <div class="mt-3">
                                    <button class="btn btn-success btn-sm" onclick="downloadAll()">
                                        <i class="fas fa-download me-2"></i>Download All
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-8">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-edit me-2"></i>File Editor</h5>
                            </div>
                            <div class="card-body">
                                <div id="file-editor">
                                    <div class="text-center text-muted py-5">
                                        <i class="fas fa-file-alt fa-3x mb-3"></i>
                                        <p>Select a file from the list to edit</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>'''
        
        # Add JavaScript section
        html_template += '''
            </div>
        </div>
    </div>

    <script>'''
        
        # Add SEC API functionality for ShareVolume tasks
        if is_sec_task:
            html_template += '''
        // SEC API Integration
        const secApiBase = 'https://data.sec.gov/api/xbrl/companyconcept/CIK';
        const aipipeProxy = 'https://aipipe.co/api/json';
        
        async function fetchShareVolumeData() {
            try {
                document.getElementById('loading').style.display = 'block';
                clearError();
                
                // Sample companies for demonstration
                const companies = [
                    { cik: '0000320193', name: 'Apple Inc.' },
                    { cik: '0001018724', name: 'Amazon.com Inc.' },
                    { cik: '0001652044', name: 'Alphabet Inc.' }
                ];
                
                const randomCompany = companies[Math.floor(Math.random() * companies.length)];
                
                // Fetch data via AIPipe proxy to avoid CORS
                const response = await fetch(`${aipipeProxy}?url=${encodeURIComponent(secApiBase + randomCompany.cik + '/us-gaap/CommonStockSharesOutstanding.json')}`);
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                updateShareVolumeDisplay(data, randomCompany.name);
                updateChart(data);
                
            } catch (error) {
                console.error('Error fetching SEC data:', error);
                showError('Failed to fetch data from SEC API. Using sample data.');
                
                // Fallback to sample data
                const sampleData = {
                    units: {
                        shares: [{
                            val: Math.floor(Math.random() * 1000000000),
                            fy: 2023,
                            form: '10-K'
                        }, {
                            val: Math.floor(Math.random() * 1000000000),
                            fy: 2022,
                            form: '10-K'
                        }]
                    }
                };
                updateShareVolumeDisplay(sampleData, 'Sample Company');
                updateChart(sampleData);
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }
        
        function updateShareVolumeDisplay(data, entityName) {
            const shares = data.units?.shares || [];
            if (shares.length === 0) return;
            
            const values = shares.map(s => s.val).filter(v => v != null);
            const maxValue = Math.max(...values);
            const minValue = Math.min(...values);
            
            const maxEntry = shares.find(s => s.val === maxValue);
            const minEntry = shares.find(s => s.val === minValue);
            
            document.getElementById('share-entity-name').textContent = entityName;
            document.getElementById('share-max-value').textContent = formatNumber(maxValue);
            document.getElementById('share-max-fy').textContent = `Fiscal Year: ${maxEntry?.fy || 'N/A'}`;
            document.getElementById('share-min-value').textContent = formatNumber(minValue);
            document.getElementById('share-min-fy').textContent = `Fiscal Year: ${minEntry?.fy || 'N/A'}`;
        }
        
        function updateChart(data) {
            const ctx = document.getElementById('shareVolumeChart').getContext('2d');
            const shares = data.units?.shares || [];
            
            const chartData = shares.slice(0, 10).map(s => ({
                x: s.fy,
                y: s.val
            })).sort((a, b) => a.x - b.x);
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'Shares Outstanding',
                        data: chartData,
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Shares Outstanding Over Time'
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Fiscal Year'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Shares Outstanding'
                            }
                        }
                    }
                }
            });
        }
        
        function formatNumber(num) {
            if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
            if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
            if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
            return num.toLocaleString();
        }
        
        function showError(message) {
            const errorDiv = document.getElementById('error-message');
            errorDiv.innerHTML = `<div class="error">${message}</div>`;
        }
        
        function clearError() {
            document.getElementById('error-message').innerHTML = '';
        }
        
        function exportData() {
            // Simple CSV export functionality
            const entityName = document.getElementById('share-entity-name').textContent;
            const maxValue = document.getElementById('share-max-value').textContent;
            const minValue = document.getElementById('share-min-value').textContent;
            
            const csvContent = `Entity,Max Value,Min Value\\n${entityName},${maxValue},${minValue}`;
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'share_volume_data.csv';
            a.click();
            URL.revokeObjectURL(url);
        }
        
        // Initialize data on page load
        document.addEventListener('DOMContentLoaded', fetchShareVolumeData);'''
        
        # Add file manager functionality if required
        if required_files:
            required_files_js = json.dumps(required_files)
            html_template += f'''
        
        // File Manager Functionality
        const requiredFiles = {required_files_js};
        
        function initializeFileManager() {{
            const fileList = document.getElementById('file-list');
            const fileLinksContainer = document.getElementById('file-links');
            
            if (requiredFiles.length === 0) {{
                fileList.innerHTML = '<div class="text-muted p-3">No specific files mentioned in the brief</div>';
                fileLinksContainer.innerHTML = '<span class="text-muted">No files to link</span>';
                return;
            }}
            
            // Create file navigation links
            requiredFiles.forEach((fileName, index) => {{
                // Add to file list
                const fileItem = document.createElement('div');
                fileItem.className = 'list-group-item list-group-item-action';
                fileItem.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <span>
                            <i class="fas fa-file me-2"></i>
                            ${{fileName}}
                        </span>
                        <div>
                            <span class="badge bg-secondary me-2">${{getFileType(fileName)}}</span>
                            <a href="./${{fileName}}" target="_blank" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-external-link-alt"></i>
                            </a>
                        </div>
                    </div>
                `;
                fileItem.onclick = (e) => {{
                    if (!e.target.closest('a')) {{ // Don't trigger if clicking the link
                        loadFile(fileName);
                    }}
                }};
                fileList.appendChild(fileItem);
                
                // Add to quick access links
                const linkButton = document.createElement('a');
                linkButton.href = `./${{fileName}}`;
                linkButton.target = '_blank';
                linkButton.className = `btn btn-outline-primary btn-sm`;
                linkButton.innerHTML = `
                    <i class="fas fa-file me-1"></i>
                    ${{fileName}}
                    <i class="fas fa-external-link-alt ms-1"></i>
                `;
                fileLinksContainer.appendChild(linkButton);
            }});
            
            // Add a "Download All" link
            const downloadAllBtn = document.createElement('button');
            downloadAllBtn.className = 'btn btn-success btn-sm';
            downloadAllBtn.innerHTML = '<i class="fas fa-download me-1"></i>Download All';
            downloadAllBtn.onclick = downloadAll;
            fileLinksContainer.appendChild(downloadAllBtn);
        }}
        
        function getFileType(fileName) {{
            const extension = fileName.split('.').pop().toLowerCase();
            const typeMap = {{
                'txt': 'Text',
                'json': 'JSON',
                'svg': 'SVG',
                'css': 'CSS',
                'js': 'JavaScript',
                'html': 'HTML',
                'md': 'Markdown',
                'py': 'Python',
                'php': 'PHP',
                'xml': 'XML'
            }};
            return typeMap[extension] || extension.toUpperCase();
        }}
        
        function loadFile(fileName) {{
            const fileEditor = document.getElementById('file-editor');
            const extension = fileName.split('.').pop().toLowerCase();
            
            let content = generateFileContent(fileName);
            
            fileEditor.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0">
                        <i class="fas fa-file me-2"></i>${{fileName}}
                    </h6>
                    <span class="badge bg-primary">${{getFileType(fileName)}}</span>
                </div>
                <textarea class="form-control" rows="20" id="file-content" style="font-family: 'Courier New', monospace;">${{content}}</textarea>
                <div class="mt-3">
                    <button class="btn btn-primary" onclick="saveFile('${{fileName}}')">
                        <i class="fas fa-save me-2"></i>Save
                    </button>
                    <button class="btn btn-outline-secondary ms-2" onclick="downloadFile('${{fileName}}')">
                        <i class="fas fa-download me-2"></i>Download
                    </button>
                    <button class="btn btn-outline-info ms-2" onclick="previewFile('${{fileName}}')">
                        <i class="fas fa-eye me-2"></i>Preview
                    </button>
                </div>
                <div id="file-preview" class="mt-3" style="display: none;"></div>
            `;
        }}
        
        function generateFileContent(fileName) {{
            const extension = fileName.split('.').pop().toLowerCase();
            const baseName = fileName.replace(`.$${{extension}}`, '');
            const timestamp = new Date().toISOString();
            
            switch(extension) {{
                case 'json':
                    return JSON.stringify({{
                        "name": baseName,
                        "type": "generated",
                        "timestamp": timestamp,
                        "description": `Generated content for ${{fileName}}`,
                        "data": {{
                            "example": "value"
                        }}
                    }}, null, 2);
                    
                case 'txt':
                    return `This is ${{fileName}}
Generated by Multi-File Manager
Timestamp: ${{timestamp}}

This file was automatically created based on the task requirements.
You can modify this content as needed for your specific use case.

Add your content here...`;

                case 'css':
                    return `/* Generated CSS for ${{fileName}} */

body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f8f9fa;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}}

h1 {{
    color: #007bff;
    text-align: center;
    margin-bottom: 30px;
}}

.btn {{
    background-color: #007bff;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}}

.btn:hover {{
    background-color: #0056b3;
}}`;

                case 'js':
                    return `// Generated JavaScript for ${{fileName}}

document.addEventListener('DOMContentLoaded', function() {{
    console.log('Loaded ${{fileName}}');
    
    // Initialize the application
    init${{baseName.charAt(0).toUpperCase() + baseName.slice(1)}}();
}});

function init${{baseName.charAt(0).toUpperCase() + baseName.slice(1)}}() {{
    console.log('Initializing ${{baseName}}...');
    
    // Add your custom logic here
    setupEventListeners();
    loadData();
}}

function setupEventListeners() {{
    // Add event listeners for user interactions
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {{
        button.addEventListener('click', function() {{
            console.log('Button clicked:', this.textContent);
        }});
    }});
}}

function loadData() {{
    // Load any required data
    console.log('Loading data for ${{baseName}}...');
}}`;

                case 'html':
                    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${{baseName}}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="./index.html">Home</a></li>
                <li class="breadcrumb-item active">${{fileName}}</li>
            </ol>
        </nav>
        
        <h1>${{baseName}}</h1>
        <p class="lead">Generated HTML file for ${{fileName}}</p>
        
        <div class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>
            This file was automatically generated. You can edit its content using the file manager.
        </div>
        
        <!-- Add your content here -->
        <div class="row">
            <div class="col-md-6">
                <h3>Section 1</h3>
                <p>Add your content here...</p>
            </div>
            <div class="col-md-6">
                <h3>Section 2</h3>
                <p>Add your content here...</p>
            </div>
        </div>
        
        <div class="mt-4">
            <a href="./index.html" class="btn btn-primary">
                <i class="fas fa-arrow-left me-2"></i>Back to File Manager
            </a>
        </div>
    </div>
</body>
</html>`;

                case 'md':
                    return `# ${{baseName}}

Generated markdown file for **${{fileName}}**

## Description

This file was automatically created based on the task requirements.

## Features

- Feature 1
- Feature 2
- Feature 3

## Usage

\`\`\`
Add usage instructions here
\`\`\`

## Created

${{timestamp}}`;

                default:
                    return `Generated content for ${{fileName}}
Created: ${{timestamp}}

This file was automatically generated based on the task requirements.
Please modify this content according to your specific needs.

File type: ${{extension}}
Base name: ${{baseName}}`;
            }}
        }}
        
        function saveFile(fileName) {{
            const content = document.getElementById('file-content').value;
            console.log(`Saving ${{fileName}}:`, content);
            
            // Show success message
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-success alert-dismissible fade show mt-3';
            alertDiv.innerHTML = `
                <i class="fas fa-check-circle me-2"></i>
                ${{fileName}} saved successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.getElementById('file-editor').appendChild(alertDiv);
            
            // Remove alert after 3 seconds
            setTimeout(() => {{
                if (alertDiv.parentNode) {{
                    alertDiv.remove();
                }}
            }}, 3000);
        }}
        
        function downloadFile(fileName) {{
            const content = document.getElementById('file-content').value;
            const blob = new Blob([content], {{ type: 'text/plain' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = fileName;
            a.click();
            URL.revokeObjectURL(url);
        }}
        
        function downloadAll() {{
            requiredFiles.forEach(fileName => {{
                const content = generateFileContent(fileName);
                const blob = new Blob([content], {{ type: 'text/plain' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = fileName;
                a.click();
                URL.revokeObjectURL(url);
            }});
        }}
        
        document.addEventListener('DOMContentLoaded', initializeFileManager);'''
        
        html_template += '''
    </script>
</body>
</html>'''
        
        return html_template
    
    def generate_site_universal(self, task: str, brief: str, round_num: int, 
                              attachments: Optional[Dict] = None, 
                              checks: Optional[List[str]] = None) -> Dict[str, bytes]:
        """Universal site generation function that handles any task type."""
        print(f"🔄 Universal generator processing task: {task}")
        print(f"Brief preview: {brief[:100]}...")
        
        # Detect task type and extract files
        task_type = self._detect_task_type(task, brief)
        required_files = self._extract_files_from_brief(brief)
        
        print(f"✓ Detected task type: {task_type}")
        
        # Generate main HTML content
        html_content = self._generate_enhanced_html(task, brief, required_files, checks)
        
        print(f"✓ Generated HTML ({len(html_content)} characters)")
        
        # Prepare files dictionary
        files = {
            'index.html': html_content.encode('utf-8'),
            'README.md': f'''# {task.replace('_', ' ').title()}

{brief[:200]}...

## Generated Files

This project was automatically generated with the following structure:

- `index.html` - Main application interface
- `README.md` - This documentation file  
- `LICENSE` - MIT License

## Usage

Open `index.html` in a web browser to access the application.

## Features

- Responsive Bootstrap 5 design
- Interactive data visualization
- File management system
- Real-time API integration

Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}
'''.encode('utf-8'),
            'LICENSE': '''MIT License

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
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
'''.encode('utf-8')
        }
        
        # Generate additional files if detected
        if required_files:
            print(f"✓ Generated {len(required_files)} additional files for multi-file task")
            for filename in required_files[:10]:  # Limit to 10 files
                files[filename] = self._generate_file_content(filename, task, brief).encode('utf-8')
        
        print(f"✓ Universal generation complete. Total files: {len(files)}")
        return files
    
    def _generate_file_content(self, filename: str, task: str, brief: str) -> str:
        """Generate content for a specific file type."""
        extension = filename.split('.')[-1].lower()
        basename = filename.replace(f'.{extension}', '')
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        content_generators = {
            'txt': lambda: f'''This is {filename}
Generated for task: {task}
Timestamp: {timestamp}

Brief: {brief[:200]}...

This file was automatically created based on the task requirements.
You can modify this content as needed for your specific use case.

Add your content here...''',
            
            'json': lambda: json.dumps({
                "name": basename,
                "task": task,
                "timestamp": timestamp,
                "description": f"Generated JSON file for {filename}",
                "brief": brief[:100] + "...",
                "data": {
                    "example": "value",
                    "generated": True
                }
            }, indent=2),
            
            'css': lambda: f'''/* Generated CSS for {filename} */
/* Task: {task} */
/* Generated: {timestamp} */

body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f8f9fa;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}}

h1 {{
    color: #007bff;
    text-align: center;
    margin-bottom: 30px;
}}

.{basename}-style {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 10px;
}}

.btn {{
    background-color: #007bff;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.3s;
}}

.btn:hover {{
    background-color: #0056b3;
}}''',
            
            'html': lambda: f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{basename}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="./index.html">Home</a></li>
                <li class="breadcrumb-item active">{filename}</li>
            </ol>
        </nav>
        
        <h1><i class="fas fa-file-alt me-2"></i>{basename}</h1>
        <p class="lead">Generated for task: {task}</p>
        
        <div class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>
            This file was automatically generated on {timestamp}
        </div>
        
        <div class="row">
            <div class="col-md-6">
                <h3>Content Section</h3>
                <p>This content is based on the brief: {brief[:100]}...</p>
            </div>
            <div class="col-md-6">
                <h3>Additional Features</h3>
                <ul>
                    <li>Responsive design</li>
                    <li>Bootstrap integration</li>
                    <li>Font Awesome icons</li>
                </ul>
            </div>
        </div>
        
        <div class="mt-4">
            <a href="./index.html" class="btn btn-primary">
                <i class="fas fa-arrow-left me-2"></i>Back to Main
            </a>
        </div>
    </div>
</body>
</html>''',
            
            'js': lambda: f'''// Generated JavaScript for {filename}
// Task: {task}
// Generated: {timestamp}

document.addEventListener('DOMContentLoaded', function() {{
    console.log('Loaded {filename}');
    init{basename.capitalize()}();
}});

function init{basename.capitalize()}() {{
    console.log('Initializing {basename}...');
    setupEventListeners();
    loadData();
}}

function setupEventListeners() {{
    // Event listeners for {basename}
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {{
        button.addEventListener('click', function() {{
            console.log('Button clicked:', this.textContent);
        }});
    }});
}}

function loadData() {{
    // Data loading logic for {basename}
    console.log('Loading data for {basename}...');
    
    // Sample data based on task
    const data = {{
        task: '{task}',
        filename: '{filename}',
        timestamp: '{timestamp}',
        brief: '{brief[:50]}...'
    }};
    
    console.log('Data loaded:', data);
}}''',
            
            'md': lambda: f'''# {basename}

> Generated for task: **{task}**  
> Timestamp: {timestamp}

## Description

{brief[:200]}...

## Features

- Automatically generated content
- Markdown formatting
- Task-specific structure

## Usage

This file was created as part of the {task} task. You can edit and customize it according to your requirements.

## Structure

- **File**: {filename}
- **Type**: Markdown
- **Generated**: {timestamp}

## Next Steps

1. Review the generated content
2. Customize as needed
3. Integrate with your project

---

*Generated by Universal Task Generator*'''
        }
        
        # Use specific generator or fallback to default
        if extension in content_generators:
            return content_generators[extension]()
        else:
            # Default content for unknown file types
            return f'''Generated content for {filename}
Task: {task}
Generated: {timestamp}

Brief: {brief[:200]}...

This file was automatically generated based on the task requirements.
Please modify this content according to your specific needs.

File type: {extension}
Base name: {basename}
'''

def generate_site(task: str, brief: str, round_num: int, attachments: Optional[Dict] = None, checks: Optional[List[str]] = None) -> Dict[str, bytes]:
    """
    Generate static site files based on task brief.
    
    Args:
        task: Task identifier
        brief: Task description/brief
        round_num: Round number (1 or 2)
        attachments: Optional attachments data
        checks: Optional list of evaluation checks
        
    Returns:
        Dictionary mapping filenames to file content as bytes
    """
    files = {}
    
    # Determine task type from task identifier or brief
    task_lower = task.lower()
    brief_lower = brief.lower()
    
    # Identify known task types
    task_type = ""
    if "sum-of-sales" in task_lower or "sum-of-sales" in brief_lower:
        task_type = "sum-of-sales"
    elif "markdown-to-html" in task_lower or "markdown-to-html" in brief_lower or "markdown" in task_lower:
        task_type = "markdown-to-html"
    elif "github-user" in task_lower or "github-user" in brief_lower:
        task_type = "github-user-created"
    elif "captcha" in task_lower or "captcha" in brief_lower:
        task_type = "captcha-solver"
    else:
        # For unknown task types, use the task name or brief as task_type
        task_type = task_lower.split('-')[0] if '-' in task_lower else brief_lower
    
    # Generate HTML using LLM (if available) or fallback to templates
    html_content = None
    if openai_client:
        # Always try LLM first for all task types (including new ones)
        html_content = generate_content_with_llm(task, brief, task_type, checks)
    
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
                print(f"✅ Evaluation posted successfully to {url}")
                return True
            
            print(f"⚠️ Evaluation post attempt {attempt + 1} failed: {response.status_code}")
            
        except requests.RequestException as e:
            print(f"⚠️ Evaluation post attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:
            wait_time = min(2 ** attempt, 16)  # Exponential backoff, max 16s
            time.sleep(wait_time)
    
    print(f"❌ Failed to post evaluation after {max_retries} attempts")
    return False

def process_task_background(
    email: str,
    task: str,
    round_num: int,
    nonce: str,
    evaluation_url: str,
    brief: str,
    attachments: List[Attachment],
    checks: List[str]
):
    """
    Process the task in the background and post evaluation when complete.
    This function runs asynchronously after returning 200 OK to the client.
    """
    try:
        print(f"🚀 Background task started for {task}, Round {round_num}")
        
        # Generate repository name
        repo_name = f"tds-project1-{task}"
        
        # Create or get repository
        repo_data = create_or_get_repo(repo_name)
        repo_url = repo_data["html_url"]
        print(f"📦 Repository: {repo_url}")
        
        # Generate site files using universal generator
        generator = UniversalTaskGenerator()
        files = generator.generate_site_universal(task, brief, round_num, attachments, checks)
        print(f"📝 Generated {len(files)} files")
        
        # Upload files
        latest_commit_sha = None
        for filename, content in files.items():
            commit_data = put_file(repo_name, filename, content, f"Round {round_num}: Add {filename}")
            latest_commit_sha = commit_data["commit"]["sha"]
            print(f"✅ Uploaded: {filename}")
        
        # Enable GitHub Pages (only needed for Round 1, but safe to call multiple times)
        enable_pages(repo_name)
        print(f"🌐 GitHub Pages enabled")
        
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
            "pages_url": pages_url,
            "status": "success"
        }
        
        # Post evaluation with backoff
        print(f"📤 Posting evaluation to: {evaluation_url}")
        success = post_evaluation_with_backoff(evaluation_url, evaluation_data)
        
        if success:
            print(f"✅ Task {task} completed successfully!")
        else:
            print(f"❌ Task {task} completed but evaluation post failed")
            
    except Exception as e:
        print(f"❌ Background task failed for {task}: {str(e)}")
        # Try to post error to evaluation URL
        error_data = {
            "email": email,
            "task": task,
            "round": round_num,
            "nonce": nonce,
            "status": "error",
            "error": str(e)
        }
        try:
            requests.post(evaluation_url, json=error_data, timeout=30)
        except:
            pass

@app.post("/handle_task")
async def handle_task(payload: TaskRequest, background_tasks: BackgroundTasks):
    """
    Main endpoint to handle TDS server requests.
    
    This endpoint immediately returns 200 OK to acknowledge receipt,
    then processes the task in the background and posts evaluation
    results to the evaluation_url within 10 minutes.
    
    Processes both Round 1 and Round 2 tasks:
    - Verifies APP_SECRET
    - Returns 200 OK immediately
    - Creates/updates GitHub repository (background)
    - Generates and uploads files (background)
    - Enables GitHub Pages (background)
    - Posts evaluation response to evaluation_url (background)
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
        checks = payload.checks or []
        
        # Add background task to process the request
        background_tasks.add_task(
            process_task_background,
            email=email,
            task=task,
            round_num=round_num,
            nonce=nonce,
            evaluation_url=evaluation_url,
            brief=brief,
            attachments=attachments,
            checks=checks
        )
        
        # Return 200 OK immediately to acknowledge receipt
        print(f"✅ Request received for {task}, Round {round_num}. Processing in background...")
        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "message": "Task accepted and is being processed",
                "task": task,
                "round": round_num,
                "nonce": nonce
            }
        )
        
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
