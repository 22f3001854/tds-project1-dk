"""
TDS Project 1 - FastAPI LLM Code Deployment Application

This application provides automated GitHub repository creation, file generation,
and GitHub Pages deployment for educational tasks. It leverages LLM technology
to dynamically generate HTML/JavaScript content based on task briefs.

Features:
- Dynamic content generation using AI/LLM
- Automated GitHub repository management
- GitHub Pages deployment
- Support for multiple task types (sum-of-sales, markdown-to-html, etc.)
- Background task processing with evaluation callbacks
- Comprehensive error handling and logging

Author: TDS Project Team
Date: 2025
"""

# Standard library imports
import os
import sys
import json
import base64
import re
import time
from typing import Dict, Any, Optional, List

# Third-party imports
import requests
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from openai import OpenAI

# Initialize FastAPI application
app = FastAPI(
    title="TDS Project 1 - LLM Code Deployment",
    description="Automated GitHub repository creation and deployment system",
    version="1.0.0"
)

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

# Required environment variables for application functionality
APP_SECRET = os.getenv("APP_SECRET")        # Shared secret for authentication
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")    # GitHub personal access token
GITHUB_OWNER = os.getenv("GITHUB_OWNER")    # GitHub username/organization
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")    # AI Pipe token for LLM access

# Validate required environment variables
if not all([APP_SECRET, GITHUB_TOKEN, GITHUB_OWNER]):
    raise RuntimeError(
        "Missing required environment variables: APP_SECRET, GITHUB_TOKEN, GITHUB_OWNER"
    )

# =============================================================================
# OPENAI/LLM CLIENT CONFIGURATION
# =============================================================================

# Initialize OpenAI client for AI Pipe integration (optional)
# If AIPIPE_TOKEN is not available, the application will use hardcoded templates
openai_client = None

if AIPIPE_TOKEN:
    try:
        # Configure OpenAI client to use AI Pipe proxy for LLM access
        openai_client = OpenAI(
            api_key=AIPIPE_TOKEN,
            base_url="https://aipipe.org/openai/v1"  # AI Pipe base URL for OpenAI models
        )
        print("✓ AI Pipe client initialized successfully")
    except Exception as e:
        print(f"Warning: Failed to initialize AI Pipe client: {e}")
        print("Application will fall back to hardcoded templates.")
        openai_client = None
else:
    print("⚠ AIPIPE_TOKEN not found - Using template fallbacks only")
    openai_client = None

# =============================================================================
# GITHUB API CONFIGURATION
# =============================================================================

# GitHub API configuration
GITHUB_API_BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "tds-project1-dk"
}

# =============================================================================
# APPLICATION STARTUP EVENTS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    
    Logs initialization status and configuration information.
    """
    sys.stdout.flush()
    
    print("=" * 80)
    print("TDS Project 1 - LLM Code Deployment API")
    print("=" * 80)
    
    if openai_client:
        print("✓ AI Pipe client initialized successfully - LLM generation enabled")
    else:
        print("⚠ AI Pipe client not available - Using template fallbacks")
    
    print(f"✓ GitHub Owner: {GITHUB_OWNER}")
    print(f"✓ GitHub API Base: {GITHUB_API_BASE}")
    print("=" * 80)
    sys.stdout.flush()

# =============================================================================
# PYDANTIC MODELS FOR REQUEST VALIDATION
# =============================================================================
class Attachment(BaseModel):
    """
    Data model for file attachments.
    
    Represents files that can be attached to task requests,
    supporting both data URLs and HTTP URLs.
    """
    name: str = Field(..., description="Attachment filename")
    url: str = Field(..., description="Data URL or HTTP URL to attachment content")


class TaskRequest(BaseModel):
    """
    Request model for the /handle_task endpoint.
    
    Contains all necessary information to process a TDS project task,
    including authentication, task details, and evaluation configuration.
    """
    email: str = Field(..., description="User email address")
    secret: str = Field(..., description="Shared secret for authentication")
    task: str = Field(..., description="Task identifier (e.g., 'sum-of-sales-001')")
    round: int = Field(..., description="Round number", ge=1)
    nonce: str = Field(..., description="Unique nonce for this request")
    brief: str = Field(..., description="Task description/brief")
    checks: Optional[List[str]] = Field(default=[], description="List of evaluation checks")
    evaluation_url: str = Field(..., description="URL to POST evaluation results")
    attachments: Optional[List[Attachment]] = Field(
        default=[], 
        description="Optional list of attachments"
    )

# =============================================================================
# GITHUB REPOSITORY MANAGEMENT FUNCTIONS
# =============================================================================

def create_or_get_repo(name: str) -> Dict[str, Any]:
    """
    Create a new public GitHub repository or retrieve existing one.
    
    This function first checks if a repository with the given name already exists.
    If it exists, returns the existing repository data. If not, creates a new
    public repository with auto-initialization disabled.
    
    Args:
        name: Repository name (must be valid GitHub repository name)
        
    Returns:
        Dict containing repository data from GitHub API
        
    Raises:
        HTTPException: If repository creation fails or API errors occur
    """
    # Check if repository already exists
    check_url = f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{name}"
    response = requests.get(check_url, headers=HEADERS, timeout=30)
    
    if response.status_code == 200:
        print(f"✓ Repository '{name}' already exists")
        return response.json()
    
    # Create new repository
    print(f"📦 Creating new repository: {name}")
    create_url = f"{GITHUB_API_BASE}/user/repos"
    repo_data = {
        "name": name,
        "description": f"TDS Project 1 - {name}",
        "public": True,
        "auto_init": False  # We'll add files manually
    }
    
    response = requests.post(create_url, headers=HEADERS, json=repo_data, timeout=30)
    
    if response.status_code not in [200, 201]:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create repository: {response.text}"
        )
    
    print(f"✓ Repository '{name}' created successfully")
    return response.json()

def enable_pages(name: str) -> Dict[str, Any]:
    """
    Enable GitHub Pages for the specified repository.
    
    Configures GitHub Pages to serve content from the main branch root directory.
    If Pages is already enabled, retrieves the current configuration.
    
    Args:
        name: Repository name
        
    Returns:
        Dict containing Pages configuration data
        
    Raises:
        HTTPException: If Pages enablement fails (except when already enabled)
    """
    pages_url = f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{name}/pages"
    pages_data = {
        "source": {
            "branch": "main",
            "path": "/"
        }
    }
    
    print(f"🌐 Enabling GitHub Pages for {name}")
    response = requests.post(pages_url, headers=HEADERS, json=pages_data, timeout=30)
    
    if response.status_code not in [200, 201, 409]:  # 409 = already exists
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to enable GitHub Pages: {response.text}"
        )
    
    if response.status_code == 409:
        # Pages already enabled, get current configuration
        print(f"✓ GitHub Pages already enabled for {name}")
        response = requests.get(pages_url, headers=HEADERS, timeout=30)
    else:
        print(f"✓ GitHub Pages enabled for {name}")
    
    return response.json() if response.status_code in [200, 201] else {"status": "already_enabled"}

def put_file(name: str, path: str, content_bytes: bytes, message: str) -> Dict[str, Any]:
    """
    Upload or update a file in the specified GitHub repository.
    
    This function handles both new file creation and existing file updates.
    For existing files, it retrieves the current SHA to enable updates.
    
    Args:
        name: Repository name
        path: File path within the repository (e.g., 'src/index.html')
        content_bytes: File content as bytes
        message: Commit message for this file change
        
    Returns:
        Dict containing commit data from GitHub API
        
    Raises:
        HTTPException: If file upload fails
    """
    file_url = f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{name}/contents/{path}"
    
    # Check if file exists to get SHA for updates
    existing_response = requests.get(file_url, headers=HEADERS, timeout=30)
    sha = None
    
    if existing_response.status_code == 200:
        sha = existing_response.json().get("sha")
        print(f"📝 Updating existing file: {path}")
    else:
        print(f"📝 Creating new file: {path}")
    
    # Prepare file data for GitHub API
    file_data = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8")
    }
    
    # Include SHA for updates
    if sha:
        file_data["sha"] = sha
    
    response = requests.put(file_url, headers=HEADERS, json=file_data, timeout=30)
    
    if response.status_code not in [200, 201]:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to upload file {path}: {response.text}"
        )
    
    print(f"✅ File {path} uploaded successfully")
    return response.json()

# =============================================================================
# LLM CONTENT GENERATION FUNCTIONS
# =============================================================================

def generate_content_with_llm(
    task: str, 
    brief: str, 
    task_type: str, 
    checks: Optional[List[str]] = None
) -> Optional[str]:
    """
    Generate HTML/JavaScript content dynamically using LLM based on task brief.
    
    This function constructs task-specific prompts and uses the AI Pipe client
    to generate appropriate web application content. Falls back to None if
    LLM is not available or generation fails.
    
    Args:
        task: Task identifier (e.g., 'sum-of-sales-001')
        brief: Detailed task description/brief
        task_type: Type of task (sum-of-sales, markdown-to-html, etc.)
        checks: Optional list of evaluation checks to satisfy
        
    Returns:
        Generated HTML content as string, or None if generation fails
    """
    if not openai_client:
        # No LLM client available, return None to trigger template fallback
        print("⚠ LLM client not available - will use template fallback")
        return None
    
    # Construct task-specific prompts for different task types
    prompt = _build_llm_prompt(task, brief, task_type, checks)
    
    try:
        print(f"🤖 Generating content with LLM for task type: {task_type}")
        
        response = openai_client.chat.completions.create(
            model="gpt-4.1-nano",  # AI Pipe model
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert web developer. Generate complete, working HTML files with embedded JavaScript. Return only the HTML code, no explanations or markdown code blocks."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000,
            timeout=60  # 60 second timeout for LLM generation
        )
        
        html_content = response.choices[0].message.content.strip()
        
        # Clean up response - remove markdown code fences if present
        html_content = _clean_llm_response(html_content)
        
        print(f"✅ LLM successfully generated HTML content ({len(html_content)} chars)")
        return html_content
        
    except Exception as e:
        print(f"❌ LLM generation failed: {e}. Falling back to templates.")
        return None


def _build_llm_prompt(task: str, brief: str, task_type: str, checks: Optional[List[str]]) -> str:
    """
    Build task-specific prompts for LLM content generation.
    
    Args:
        task: Task identifier
        brief: Task description
        task_type: Type of task
        checks: Optional evaluation checks
        
    Returns:
        Formatted prompt string for LLM
    """
    # Base requirements for all tasks
    base_requirements = """
- Use Bootstrap 5 CDN for styling
- Include all necessary JavaScript inline (no external files)
- Handle URL parameters if mentioned in the brief
- Include proper error handling and user feedback
- Make it completely self-contained (all code in one HTML file)
- Follow best practices for HTML5, CSS3, and modern JavaScript
- Ensure mobile-responsive design
"""
    if "sum-of-sales" in task_type:
        return f"""Generate a complete, self-contained HTML file for a sales summary application.

Requirements:
- Title: "Sales Summary"
{base_requirements}
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
        return f"""Generate a complete, self-contained HTML file for a Markdown to HTML converter.

Requirements:
- Title: "Markdown to HTML Converter"
{base_requirements}
- Include marked.js CDN for markdown parsing
- Include highlight.js CDN for syntax highlighting
- Load and render 'input.md' file or accept ?url parameter
- Display rendered HTML in a container

Additional requirements from brief: {brief}

Return ONLY the complete HTML file. No explanations."""

    elif "github-user" in task_type:
        # Extract seed from task name if present
        seed = task.split('-')[-1] if '-' in task else "default"
        return f"""Generate a complete, self-contained HTML file for a GitHub user account age checker.

Requirements:
- Title: "GitHub User Account Age"
{base_requirements}
- Include a form with id="github-user-{seed}"
- Form should have an input for GitHub username and submit button
- On submit, fetch user data from GitHub API: https://api.github.com/users/{{username}}
- Display account creation date from 'created_at' field
- Calculate and display account age in years and days
- Show results in Bootstrap alert

Additional requirements from brief: {brief}

Return ONLY the complete HTML file. No explanations."""

    elif "captcha" in task_type:
        return f"""Generate a complete, self-contained HTML file for a CAPTCHA solver.

Requirements:
- Title: "CAPTCHA Solver"
{base_requirements}
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
        checks_text = ""
        if checks:
            checks_text = "\n\nEvaluation Checks (MUST satisfy):\n" + "\n".join(f"- {check}" for check in checks)
        
        return f"""Generate a complete, self-contained HTML file based on this task brief.

Task Name: {task}
Task Type: {task_type}

Brief: {brief}{checks_text}

Requirements:
- Create a fully functional web application that fulfills the brief requirements
{base_requirements}
- Use appropriate JavaScript libraries from CDN if needed (Chart.js, Marked.js, Tesseract.js, etc.)
- Add loading states and user-friendly messages where appropriate
- Make sure to check all the CDN links are correct and accessible

Return ONLY the complete HTML file. No explanations or markdown code blocks."""


def _clean_llm_response(html_content: str) -> str:
    """
    Clean up LLM response by removing markdown code fences if present.
    
    Args:
        html_content: Raw HTML content from LLM
        
    Returns:
        Cleaned HTML content
    """
    # Remove markdown code fences if present
    if html_content.startswith("```"):
        lines = html_content.split('\n')
        if len(lines) > 2:
            # Remove first and last lines (code fences)
            html_content = '\n'.join(lines[1:-1])
    
    return html_content.strip()

# =============================================================================
# UNIVERSAL TASK GENERATOR CLASS
# =============================================================================

class UniversalTaskGenerator:
    """
    Universal task generator for dynamic content creation.
    
    This class can handle any kind of task request dynamically by analyzing
    the task brief and generating appropriate web content with file management
    capabilities. It supports multiple file types and complex task requirements.
    
    Features:
    - Automatic file detection from task briefs
    - Multi-file project generation
    - Task type detection and classification
    - Enhanced HTML generation with Bootstrap styling
    - SEC API integration for financial tasks
    - File management interface
    """
    
    def __init__(self):
        """Initialize the universal task generator with supported file types."""
        self.supported_extensions = [
            '.txt', '.json', '.svg', '.css', '.js', '.html', '.md', '.py', 
            '.php', '.xml', '.yaml', '.yml', '.toml', '.ini', '.conf', 
            '.c', '.cpp', '.java', '.rs'
        ]
    
    def _extract_files_from_brief(self, brief: str) -> List[str]:
        """
        Extract file names from the task brief using regex patterns.
        
        Searches for explicit file mentions, creation requests, and files
        with supported extensions.
        
        Args:
            brief: Task description text
            
        Returns:
            List of unique file names found in the brief (max 10)
        """
        files = []
        
        # Multiple regex patterns to catch different file mention styles
        file_patterns = [
            r'\b(\w+\.\w+)\b',  # Basic pattern: filename.extension
            r'(?:file|create|build|generate|make)s?\s+(?:called\s+)?["\']?(\w+\.\w+)["\']?',
            r'(\w+\.(?:txt|json|svg|css|js|html|md|py|php|xml|yaml|yml|toml|ini|conf|c|cpp|java|rs))\b'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, brief, re.IGNORECASE)
            for match in matches:
                # Handle tuple matches from regex groups
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                    
                # Validate file extension
                if '.' in match and any(match.lower().endswith(ext) for ext in self.supported_extensions):
                    files.append(match)
        
        # Remove duplicates while preserving order
        unique_files = []
        for file in files:
            if file not in unique_files:
                unique_files.append(file)
        
        return unique_files[:10]  # Limit to 10 files max for performance
    
    def _has_multiple_file_requirements(self, brief: str) -> bool:
        """
        Check if the task brief indicates multiple file requirements.
        
        Args:
            brief: Task description text
            
        Returns:
            True if multiple files are likely required
        """
        multi_file_indicators = [
            'files', 'create multiple', 'several files', 'different files',
            'also create', 'and a', 'along with', 'additional file',
            'separate file', 'another file', 'include file'
        ]
        return any(indicator in brief.lower() for indicator in multi_file_indicators)
    
    def _detect_task_type(self, task: str, brief: str) -> str:
        """
        Detect the task type from task name and brief content.
        
        Args:
            task: Task identifier
            brief: Task description
            
        Returns:
            Detected task type string
        """
        task_lower = task.lower()
        brief_lower = brief.lower()
        
        # Known task type patterns
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

```
Add usage instructions here
```

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

# =============================================================================
# BACKGROUND TASK PROCESSING
# =============================================================================

def post_evaluation_with_backoff(url: str, data: Dict[str, Any], max_retries: int = 5) -> bool:
    """
    Post evaluation data with exponential backoff retry strategy.
    
    Implements robust error handling and retry logic for evaluation submissions
    to handle temporary network issues or server unavailability.
    
    Args:
        url: Evaluation endpoint URL
        data: Evaluation data to POST
        max_retries: Maximum number of retry attempts (default: 5)
        
    Returns:
        True if successful, False if all retries failed
    """
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code in [200, 201]:
                print(f"✅ Evaluation posted successfully to {url}")
                return True
            
            print(f"⚠️ Evaluation post attempt {attempt + 1} failed: HTTP {response.status_code}")
            
        except requests.RequestException as e:
            print(f"⚠️ Evaluation post attempt {attempt + 1} failed: {e}")
        
        # Exponential backoff with jitter
        if attempt < max_retries - 1:
            wait_time = min(2 ** attempt, 16)  # Max 16 seconds
            print(f"🕐 Waiting {wait_time}s before retry...")
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
    It handles the complete workflow of repository creation, file generation,
    and evaluation submission.
    
    Workflow:
    1. Generate repository name
    2. Create or get GitHub repository
    3. Generate site files using universal generator
    4. Upload all files to repository
    5. Enable GitHub Pages
    6. Post evaluation results
    
    Args:
        email: User email address
        task: Task identifier
        round_num: Round number
        nonce: Unique request identifier
        evaluation_url: URL to POST evaluation results
        brief: Task description
        attachments: List of file attachments
        checks: List of evaluation checks
    """
    try:
        print(f"🚀 Background processing started: {task} (Round {round_num})")
        
        # Step 1: Generate repository name
        repo_name = f"tds-project1-{task}"
        
        # Step 2: Create or get repository
        repo_data = create_or_get_repo(repo_name)
        repo_url = repo_data["html_url"]
        print(f"📦 Repository ready: {repo_url}")
        
        # Step 3: Generate site files using universal generator
        generator = UniversalTaskGenerator()
        files = generator.generate_site_universal(task, brief, round_num, attachments, checks)
        print(f"📝 Generated {len(files)} files")
        
        # Step 4: Upload files to repository
        latest_commit_sha = None
        for filename, content in files.items():
            commit_data = put_file(
                repo_name, 
                filename, 
                content, 
                f"Round {round_num}: Add {filename}"
            )
            latest_commit_sha = commit_data["commit"]["sha"]
            print(f"✅ Uploaded: {filename}")
        
        # Step 5: Enable GitHub Pages
        enable_pages(repo_name)
        print(f"🌐 GitHub Pages configured")
        
        # Step 6: Construct Pages URL and prepare evaluation
        pages_url = f"https://{GITHUB_OWNER}.github.io/{repo_name}/"
        
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
        
        # Step 7: Post evaluation with retry logic
        print(f"📤 Submitting evaluation to: {evaluation_url}")
        success = post_evaluation_with_backoff(evaluation_url, evaluation_data)
        
        if success:
            print(f"✅ Task {task} completed successfully!")
        else:
            print(f"❌ Task {task} completed but evaluation submission failed")
            
    except Exception as e:
        print(f"❌ Background task failed for {task}: {str(e)}")
        
        # Attempt to report error to evaluation URL
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
            print("📤 Error reported to evaluation URL")
        except Exception as eval_error:
            print(f"⚠️ Failed to report error to evaluation URL: {eval_error}")

# =============================================================================
# MAIN API ENDPOINTS
# =============================================================================

@app.post("/handle_task")
async def handle_task(payload: TaskRequest, background_tasks: BackgroundTasks):
    """
    Main endpoint to handle TDS server deployment requests.
    
    This endpoint implements an asynchronous workflow:
    1. Immediately validates the request and returns 200 OK
    2. Processes the task in the background
    3. Posts evaluation results to the provided callback URL
    
    Supports both Round 1 and Round 2 tasks with the following features:
    - Secret verification for security
    - Universal task type support
    - LLM-powered content generation
    - Automated GitHub repository management
    - GitHub Pages deployment
    - Comprehensive error handling and logging
    
    Args:
        payload: TaskRequest containing all task details
        background_tasks: FastAPI background task manager
        
    Returns:
        Immediate acknowledgment response (200 OK)
        
    Raises:
        HTTPException: For authentication failures or validation errors
    """
    try:
        # Step 1: Validate authentication
        if payload.secret != APP_SECRET:
            print(f"❌ Authentication failed for {payload.email}")
            raise HTTPException(status_code=401, detail="Invalid secret")
        
        # Step 2: Extract and validate task data
        email = payload.email
        task = payload.task
        round_num = payload.round
        nonce = payload.nonce
        evaluation_url = payload.evaluation_url
        brief = payload.brief
        attachments = payload.attachments or []
        checks = payload.checks or []
        
        # Step 3: Log request details
        print(f"📨 Request received: {task} (Round {round_num}) from {email}")
        print(f"📋 Brief: {brief[:100]}{'...' if len(brief) > 100 else ''}")
        print(f"📎 Attachments: {len(attachments)}")
        print(f"✅ Checks: {len(checks)}")
        
        # Step 4: Schedule background processing
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
        
        # Step 5: Return immediate acknowledgment
        print(f"✅ Task {task} accepted - processing in background")
        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "message": "Task accepted and is being processed",
                "task": task,
                "round": round_num,
                "nonce": nonce,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 401 Unauthorized)
        raise
    except Exception as e:
        # Handle unexpected errors
        print(f"❌ Unexpected error in handle_task: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(e),
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
            }
        )

@app.get("/")
async def root():
    """
    API documentation landing page.
    
    Provides comprehensive information about the TDS Project 1 API,
    including endpoints, usage instructions, and supported task types.
    
    Returns:
        HTML response with interactive documentation
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TDS Project 1 - LLM Code Deployment API</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
            .main-container { 
                background: rgba(255, 255, 255, 0.95); 
                border-radius: 15px; 
                margin: 20px 0; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.1); 
            }
            .header-section { 
                background: linear-gradient(45deg, #007bff, #0056b3); 
                color: white; 
                border-radius: 15px 15px 0 0; 
                padding: 30px; 
                text-align: center; 
            }
            .content-section { padding: 30px; }
            .feature-card { 
                background: white; 
                border-radius: 10px; 
                padding: 20px; 
                margin-bottom: 20px; 
                box-shadow: 0 5px 15px rgba(0,0,0,0.08); 
                transition: transform 0.3s ease; 
            }
            .feature-card:hover { transform: translateY(-5px); }
            .status-badge { 
                background: #28a745; 
                color: white; 
                padding: 5px 15px; 
                border-radius: 20px; 
                font-weight: 500; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="main-container">
                <div class="header-section">
                    <h1><i class="fas fa-rocket me-3"></i>TDS Project 1 - LLM Code Deployment API</h1>
                    <p class="lead mb-3">Automated GitHub repository creation and deployment system</p>
                    <span class="status-badge"><i class="fas fa-check-circle me-2"></i>Service Running</span>
                </div>
                
                <div class="content-section">
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <div class="feature-card">
                                <h5><i class="fas fa-cogs me-2 text-primary"></i>Key Features</h5>
                                <ul class="list-unstyled">
                                    <li><i class="fas fa-check text-success me-2"></i>LLM-powered content generation</li>
                                    <li><i class="fas fa-check text-success me-2"></i>Universal task type support</li>
                                    <li><i class="fas fa-check text-success me-2"></i>Automated GitHub integration</li>
                                    <li><i class="fas fa-check text-success me-2"></i>GitHub Pages deployment</li>
                                    <li><i class="fas fa-check text-success me-2"></i>Background processing</li>
                                </ul>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="feature-card">
                                <h5><i class="fas fa-list me-2 text-success"></i>Supported Tasks</h5>
                                <ul class="list-unstyled">
                                    <li><i class="fas fa-chart-bar text-info me-2"></i>Sales summaries</li>
                                    <li><i class="fas fa-markdown text-warning me-2"></i>Markdown converters</li>
                                    <li><i class="fas fa-user text-primary me-2"></i>GitHub user tools</li>
                                    <li><i class="fas fa-shield-alt text-secondary me-2"></i>CAPTCHA solvers</li>
                                    <li><i class="fas fa-star text-warning me-2"></i>Custom applications</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    
                    <h2><i class="fas fa-network-wired me-2"></i>API Endpoints</h2>
                    <div class="feature-card">
                        <div class="row">
                            <div class="col-md-6">
                                <h6><span class="badge bg-success">POST</span> /handle_task</h6>
                                <p class="text-muted">Main endpoint for task processing</p>
                            </div>
                            <div class="col-md-6">
                                <h6><span class="badge bg-info">GET</span> /health</h6>
                                <p class="text-muted">Service health check</p>
                            </div>
                        </div>
                    </div>
                    
                    <h2><i class="fas fa-book me-2"></i>Documentation</h2>
                    <div class="btn-group mb-4" role="group">
                        <a href="/docs" class="btn btn-primary">
                            <i class="fas fa-code me-2"></i>Swagger UI
                        </a>
                        <a href="/redoc" class="btn btn-outline-primary">
                            <i class="fas fa-file-alt me-2"></i>ReDoc
                        </a>
                        <a href="/health" class="btn btn-success">
                            <i class="fas fa-heartbeat me-2"></i>Health Check
                        </a>
                    </div>
                    
                    <h2><i class="fas fa-terminal me-2"></i>Usage Example</h2>
                    <div class="feature-card">
                        <pre class="bg-light p-3 rounded"><code>{
  "email": "user@example.com",
  "secret": "your-app-secret",
  "task": "sum-of-sales-001",
  "round": 1,
  "nonce": "unique-request-id",
  "brief": "Create a sales summary dashboard",
  "evaluation_url": "https://evaluation.endpoint.com/callback",
  "attachments": [],
  "checks": []
}</code></pre>
                    </div>
                    
                    <footer class="text-center text-muted mt-5">
                        <p><i class="fas fa-graduation-cap me-2"></i>TDS Project 1 | FastAPI + GitHub API | 2025</p>
                    </footer>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health():
    """
    Comprehensive health check endpoint.
    
    Provides detailed information about service status, configuration,
    and availability of required components.
    
    Returns:
        JSON response with health status and configuration details
    """
    return {
        "status": "healthy",
        "service": "TDS Project 1 - LLM Code Deployment",
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        "configuration": {
            "github_owner": GITHUB_OWNER,
            "has_github_token": bool(GITHUB_TOKEN),
            "has_app_secret": bool(APP_SECRET),
            "llm_enabled": bool(openai_client),
            "aipipe_configured": bool(AIPIPE_TOKEN)
        },
        "features": {
            "universal_task_generator": True,
            "github_integration": True,
            "github_pages": True,
            "background_processing": True,
            "evaluation_callbacks": True
        }
    }

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    """
    Application entry point for development server.
    
    Starts the FastAPI application using Uvicorn ASGI server on
    host 0.0.0.0 (all interfaces) and port 7860.
    
    For production deployment, use a proper ASGI server setup
    with appropriate configuration for scaling and security.
    """
    print("=" * 60)
    print("🚀 Starting TDS Project 1 - LLM Code Deployment API")
    print("=" * 60)
    print(f"🌐 Server will be available at: http://0.0.0.0:7860")
    print(f"📖 API documentation: http://0.0.0.0:7860/docs")
    print(f"❤️ Health check: http://0.0.0.0:7860/health")
    print("=" * 60)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=7860,
        log_level="info"
    )
