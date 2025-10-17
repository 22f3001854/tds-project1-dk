# Task Type Detection - How It Works

## ⚠️ **IMPORTANT: There is NO explicit "task_type" field in the input!**

The input request **DOES NOT** include a `task_type` field. Instead, the task type is **INFERRED** from two fields:

---

## 📥 **Input Request Fields**

```json
{
  "task": "captcha-solver-test-001",        ← Contains task type hint
  "brief": "Create a captcha solver...",    ← Contains task description
  ...other fields...
}
```

**Key Points:**
- ❌ NO `task_type` field in the input
- ✅ Task type is **extracted** from `task` field name
- ✅ Task type is also **detected** from `brief` field content

---

## 🔍 **How Task Type Detection Works**

### Step 1: Extract Input Fields (line 327-328)
```python
task_lower = task.lower()      # "captcha-solver-test-001"
brief_lower = brief.lower()    # "create a captcha solver..."
```

### Step 2: Pattern Matching (line 331-343)
The code searches for keywords in BOTH `task` and `brief`:

```python
task_type = ""

# Check for "sum-of-sales"
if "sum-of-sales" in task_lower or "sum-of-sales" in brief_lower:
    task_type = "sum-of-sales"

# Check for "markdown"
elif "markdown-to-html" in task_lower or "markdown" in task_lower:
    task_type = "markdown-to-html"

# Check for "github-user"
elif "github-user" in task_lower or "github-user" in brief_lower:
    task_type = "github-user-created"

# Check for "captcha"  ← THIS MATCHES YOUR EXAMPLE
elif "captcha" in task_lower or "captcha" in brief_lower:
    task_type = "captcha-solver"

# Fallback for unknown tasks
else:
    # Extract first part before hyphen
    task_type = task_lower.split('-')[0]  # e.g., "image" from "image-resize-001"
```

---

## 📝 **Examples**

### Example 1: Captcha Solver
**Input:**
```json
{
  "task": "captcha-solver-test-001",
  "brief": "Create a captcha solver that handles ?url=..."
}
```

**Detection Logic:**
```python
task_lower = "captcha-solver-test-001"
brief_lower = "create a captcha solver that handles ?url=..."

# Checks:
"captcha" in task_lower?        → ✅ YES (found in "captcha-solver-test-001")
# OR
"captcha" in brief_lower?       → ✅ YES (found in "create a captcha solver...")

# Result:
task_type = "captcha-solver"
```

---

### Example 2: Sum of Sales
**Input:**
```json
{
  "task": "sum-of-sales-001",
  "brief": "Display sales totals"
}
```

**Detection Logic:**
```python
task_lower = "sum-of-sales-001"
brief_lower = "display sales totals"

# Checks:
"sum-of-sales" in task_lower?   → ✅ YES

# Result:
task_type = "sum-of-sales"
```

---

### Example 3: Unknown Task Type
**Input:**
```json
{
  "task": "image-resize-test-001",
  "brief": "Resize images to 800x600"
}
```

**Detection Logic:**
```python
task_lower = "image-resize-test-001"
brief_lower = "resize images to 800x600"

# Checks:
"sum-of-sales" in task_lower?   → ❌ NO
"markdown" in task_lower?       → ❌ NO
"github-user" in task_lower?    → ❌ NO
"captcha" in task_lower?        → ❌ NO

# Fallback:
task_type = task_lower.split('-')[0]  # "image"
```

---

## 🎯 **Where This Happens in Code**

### File: `main.py`
### Function: `generate_site()`
### Lines: **327-343**

```python
def generate_site(task: str, brief: str, round_num: int, attachments: Optional[Dict] = None):
    """Generate static site files based on task brief."""
    
    files = {}
    
    # ⬇️ TASK TYPE DETECTION STARTS HERE
    task_lower = task.lower()
    brief_lower = brief.lower()
    
    # Identify known task types
    task_type = ""
    if "sum-of-sales" in task_lower or "sum-of-sales" in brief_lower:
        task_type = "sum-of-sales"
    elif "markdown-to-html" in task_lower or "markdown" in task_lower:
        task_type = "markdown-to-html"
    elif "github-user" in task_lower or "github-user" in brief_lower:
        task_type = "github-user-created"
    elif "captcha" in task_lower or "captcha" in brief_lower:
        task_type = "captcha-solver"
    else:
        # For unknown task types, use the task name or brief as task_type
        task_type = task_lower.split('-')[0] if '-' in task_lower else brief_lower
    # ⬆️ TASK TYPE DETECTION ENDS HERE
    
    # Now use task_type to generate content...
```

---

## 📊 **Visual Flow**

```
INPUT REQUEST
│
├─► "task": "captcha-solver-test-001"
│   └─► Convert to lowercase → "captcha-solver-test-001"
│       └─► Check if contains "captcha" → ✅ YES
│           └─► Set task_type = "captcha-solver"
│
└─► "brief": "Create a captcha solver..."
    └─► Convert to lowercase → "create a captcha solver..."
        └─► Check if contains "captcha" → ✅ YES (backup check)
            └─► Confirms task_type = "captcha-solver"

RESULT: task_type = "captcha-solver"
        ↓
        Used to generate LLM prompt
        ↓
        Creates captcha solver HTML
```

---

## 🔑 **Key Takeaways**

1. **No explicit `task_type` field** in the input request
2. **Task type is inferred** from the `task` field name
3. **Backup detection** from the `brief` field content
4. **Pattern matching** using keyword searches (`if "captcha" in task_lower`)
5. **Fallback mechanism** for unknown tasks (splits task name at `-`)

---

## 📍 **Exact Code Locations**

| What | Where | Line Numbers |
|------|-------|--------------|
| Input fields received | `handle_task()` endpoint | Line ~735 |
| Task type detection | `generate_site()` function | Lines 327-343 |
| LLM prompt generation | `generate_content_with_llm()` | Lines 181-290 |
| Captcha prompt specifically | `generate_content_with_llm()` | Lines 251-267 |

---

## ✅ **Summary**

**Question:** Where is task type given in the input?

**Answer:** 
- **Nowhere explicitly!** 
- The input only provides `"task": "captcha-solver-test-001"` and `"brief": "..."`
- Your code **extracts** the task type by searching for keywords like `"captcha"` in these fields
- This happens in `generate_site()` function at **lines 327-343** of `main.py`
