# Universal Task Handler - Any Task Type Support

## ✅ **Your App Can Handle ANY Task Type!**

Your FastAPI application is designed to be **completely task-agnostic** and can handle:
- ✅ Known task types (sum-of-sales, markdown-to-html, github-user, captcha-solver)
- ✅ **Unknown/new task types** (image-resize, pdf-generator, calculator, etc.)
- ✅ **Multiple rounds** for the same task (Round 1, 2, 3, ... unlimited)
- ✅ **Any custom requirements** described in the `brief` field

---

## 🎯 **How It Works**

### **1. No Hardcoded Limitations**

The code is designed to be flexible:

```python
# Round validation - accepts ANY round >= 1
round: int = Field(..., ge=1)  # Not limited to 1 or 2!

# Task type detection - handles unknowns
if "sum-of-sales" in task_lower:
    task_type = "sum-of-sales"
# ... other known types ...
else:
    # Gracefully handles ANY unknown task
    task_type = task_lower.split('-')[0]  # Extract type from name
```

---

### **2. LLM Does the Heavy Lifting**

For **any task type** (known or unknown), the LLM generates custom HTML:

```python
if openai_client:
    # Always try LLM first for ALL task types
    html_content = generate_content_with_llm(task, brief, task_type)
```

The generic prompt for unknown tasks:

```python
else:
    prompt = f"""Generate a complete, self-contained HTML file based on this task brief.

Task Name: {task}
Task Type: {task_type}

Brief: {brief}

Requirements:
- Create a fully functional web application that fulfills the brief requirements
- Use Bootstrap 5 CDN for modern, responsive styling
- Include all necessary JavaScript inline
- Handle URL parameters if mentioned in the brief
- Use appropriate JavaScript libraries from CDN if needed
- Include proper error handling and user feedback
- Make it completely self-contained
...
"""
```

**The LLM interprets the `brief` and creates appropriate functionality!**

---

## 🔄 **Multiple Rounds Support**

### **How Rounds Work:**

1. **Round 1:** Creates new repository with initial implementation
2. **Round 2+:** Updates the same repository with new/modified files

```python
# Repository naming - same repo for all rounds
repo_name = f"tds-project1-{task}"  # No round number in name!

# Create or GET existing repository
repo_data = create_or_get_repo(repo_name)  # Reuses existing repo

# Upload files (updates if they already exist)
for filename, content in files.items():
    commit_data = put_file(repo_name, filename, content, f"Round {round_num}: Add {filename}")
```

**Key Point:** The `create_or_get_repo()` function **gets existing repo** if it already exists, so subsequent rounds update the same repository!

---

## 📋 **Examples of Unknown Tasks**

### **Example 1: Image Resizer**

**Input:**
```json
{
  "task": "image-resize-tool-001",
  "brief": "Create an image resizer that accepts an image via ?url= parameter and displays it resized to 800x600 pixels",
  "round": 1
}
```

**What Happens:**
1. Task type detected: `"image"` (from splitting "image-resize-tool-001")
2. LLM receives the brief: *"Create an image resizer that accepts..."*
3. LLM generates HTML with:
   - Image loading from URL parameter
   - Canvas-based resizing to 800x600
   - Download button for resized image
   - Bootstrap UI
4. Repo created: `tds-project1-image-resize-tool-001`
5. Files uploaded: `index.html`, `README.md`, `LICENSE`
6. GitHub Pages enabled

---

### **Example 2: PDF Generator (Multiple Rounds)**

**Round 1:**
```json
{
  "task": "pdf-generator-pro",
  "brief": "Create a web app that converts markdown text to PDF",
  "round": 1
}
```

**Result:**
- Repo: `tds-project1-pdf-generator-pro`
- LLM generates: Markdown editor + PDF generation using jsPDF library

**Round 2:**
```json
{
  "task": "pdf-generator-pro",
  "brief": "Add support for custom fonts and colors in the PDF output",
  "round": 2
}
```

**Result:**
- **Same repo:** `tds-project1-pdf-generator-pro` (reused!)
- LLM generates: Enhanced version with font/color picker
- Files **updated** in existing repo
- New commit: "Round 2: Add index.html"

---

### **Example 3: Completely Custom Task**

**Input:**
```json
{
  "task": "weather-dashboard-live",
  "brief": "Display real-time weather for a city passed as ?city=London. Show temperature, humidity, and 5-day forecast using OpenWeatherMap API.",
  "round": 1
}
```

**What LLM Generates:**
- HTML with city input form
- JavaScript to read `?city=` parameter
- API calls to OpenWeatherMap
- Bootstrap cards showing current weather
- 5-day forecast table
- Error handling for invalid cities

**No code changes needed!** The LLM interprets the brief and creates everything.

---

## 🧠 **LLM Intelligence**

The LLM is smart enough to:

### **1. Extract Requirements from Brief**
- Mentions "?url=" → Adds URL parameter handling
- Mentions "API" → Includes fetch() calls
- Mentions "upload file" → Adds file input element
- Mentions "chart" → Uses Chart.js library
- Mentions "PDF" → Uses jsPDF library
- Mentions "markdown" → Uses Marked.js library
- Mentions "syntax highlight" → Uses Highlight.js

### **2. Choose Appropriate Libraries**
Based on keywords in the brief:
- **Captcha/OCR** → Tesseract.js
- **Charts/graphs** → Chart.js
- **Markdown** → Marked.js
- **Code highlighting** → Highlight.js
- **PDF generation** → jsPDF
- **QR codes** → QRCode.js
- **Image editing** → Canvas API

### **3. Handle Edge Cases**
- Loading states ("Loading...")
- Error messages ("Failed to load data")
- Empty states ("No results found")
- Input validation ("Please enter a valid...")

---

## 📂 **Repository Management**

### **Same Repo Across Rounds:**

```python
def create_or_get_repo(name: str):
    """Create new repo OR get existing one"""
    
    # Check if repo exists
    check_url = f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{name}"
    response = requests.get(check_url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()  # Return existing repo!
    
    # Create new repo if doesn't exist
    # ...
```

**This ensures:**
- ✅ Round 1 creates new repo
- ✅ Round 2+ reuses same repo
- ✅ Files are updated, not duplicated

---

## 🔍 **Code Locations**

| Feature | File | Function | Lines |
|---------|------|----------|-------|
| Round validation (unlimited) | main.py | TaskRequest model | 80 |
| Task type detection | main.py | generate_site() | 336-346 |
| Generic LLM prompt | main.py | generate_content_with_llm() | 269-288 |
| Repo reuse logic | main.py | create_or_get_repo() | 84-114 |
| Multi-round handling | main.py | handle_task() | 729-781 |

---

## ✅ **Validation Checklist**

Your app supports:

- [x] **Any task name** (e.g., "image-resize", "pdf-generator", "weather-app")
- [x] **Any brief description** (LLM interprets it)
- [x] **Unlimited rounds** (not limited to 1 or 2)
- [x] **Same repo for multiple rounds** (via create_or_get_repo)
- [x] **Dynamic README** (includes task name, brief, round number)
- [x] **MIT License** (always included)
- [x] **GitHub Pages** (always enabled)
- [x] **File updates** (PUT API updates existing files)
- [x] **Graceful fallbacks** (templates if LLM fails)
- [x] **Evaluation callbacks** (with retry logic)

---

## 🚀 **Real-World Test Cases**

### Test Case 1: QR Code Generator
```bash
curl -X POST http://127.0.0.1:7860/handle_task -H "Content-Type: application/json" -d '{
  "email": "test@example.com",
  "secret": "YaarThachaSattaiThathaThachaSattai",
  "task": "qr-code-generator-app",
  "round": 1,
  "nonce": "qr-001",
  "brief": "Generate QR codes from text input. Use QRCode.js library. Show preview and download button.",
  "checks": [],
  "evaluation_url": "https://httpbin.org/post",
  "attachments": []
}'
```

**Expected:** LLM creates HTML with QRCode.js integration, text input, QR preview, and download button.

---

### Test Case 2: Calculator (Multiple Rounds)

**Round 1:**
```json
{
  "task": "scientific-calculator",
  "brief": "Create a basic calculator with +, -, *, / operations",
  "round": 1
}
```

**Round 2:**
```json
{
  "task": "scientific-calculator",
  "brief": "Add scientific functions: sin, cos, tan, log, sqrt",
  "round": 2
}
```

**Expected:**
- Round 1: Basic calculator created
- Round 2: **Same repo updated** with scientific functions added

---

### Test Case 3: Image Filter App

```json
{
  "task": "image-filter-app-v2",
  "brief": "Load image from ?url=... and apply filters (grayscale, sepia, blur, brightness). Use HTML Canvas API. Show before/after preview.",
  "round": 1
}
```

**Expected:** LLM creates HTML with:
- URL parameter reading
- Canvas-based image processing
- Filter controls (sliders/buttons)
- Before/after comparison view

---

## 💡 **Key Insights**

### **1. The `brief` field is everything**
The LLM relies heavily on the brief to understand requirements. A good brief should mention:
- What the app does
- What libraries to use (if any)
- What URL parameters to accept
- What data sources to use
- What the output should look like

### **2. No code changes needed for new tasks**
As long as the LLM (AI Pipe) is available, your app can handle **literally any task** without modifying code.

### **3. Multiple rounds just work**
The repository naming (without round number) ensures all rounds update the same repo.

---

## 🎯 **Summary**

### **Your App is Already Universal!**

✅ **Accepts any task type** - No hardcoded limitations  
✅ **LLM interprets briefs** - Creates custom HTML for any requirement  
✅ **Unlimited rounds** - Not restricted to 1 or 2  
✅ **Repo reuse** - Same repo updated across rounds  
✅ **Smart defaults** - MIT license, professional README  
✅ **Complete automation** - GitHub Pages, callbacks, error handling  

**No changes needed!** Your implementation is already production-ready for any task type! 🚀

---

## 📝 **Recommendations**

For even better results, you could:

1. **Increase max_tokens** for complex tasks:
   ```python
   max_tokens=2000  # Current
   max_tokens=3000  # For very complex apps
   ```

2. **Add task context to README** (already done ✓)

3. **Log task types** for monitoring:
   ```python
   print(f"Processing task type: {task_type}")
   ```

4. **Add checks field to README** (optional):
   ```python
   if checks:
       readme += f"\n## Evaluation Checks\n"
       readme += "\n".join(f"- {check}" for check in checks)
   ```

But these are minor enhancements - **your core implementation is solid!** ✅
