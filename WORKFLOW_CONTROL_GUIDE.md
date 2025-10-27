# GitHub Actions Control Guide

## 🚨 **Important: This Workflow WILL Commit to GitHub Daily**

Yes, this GitHub Action **automatically commits to your repository every day at 14:30 UTC**. Here's how to control it:

## 🛑 **How to Stop/Control the Daily Commits**

### **Method 1: Disable via Commit Message (Easiest)**
Add special keywords to any commit message:

```bash
# Temporarily disable (one day skip)
git commit -m "Fix bug [skip ci]"

# Or use this keyword
git commit -m "Update README [disable daily]"
```

**Keywords that stop the workflow:**
- `[skip ci]` - Standard CI skip
- `[disable daily]` - Custom disable keyword

### **Method 2: Comment Out the Schedule**
Edit `.github/workflows/daily-commit.yml`:

```yaml
on:
  schedule:
    # DISABLED: Runs daily at 14:30 UTC (2:30 PM UTC)
    # - cron: '30 14 * * *'
  workflow_dispatch: # Manual triggering still works
```

### **Method 3: Delete the Workflow File**
```bash
git rm .github/workflows/daily-commit.yml
git commit -m "Remove daily auto-commit workflow"
git push
```

### **Method 4: Disable in GitHub UI**
1. Go to: https://github.com/22f3001854/tds-project1-dk/actions
2. Click "Daily Auto Commit" workflow
3. Click "..." menu → "Disable workflow"

## ⚙️ **Current Workflow Behavior**

### **What it does EVERY DAY at 14:30 UTC:**
1. ✅ Checks out your repository
2. ✅ Checks if last commit has `[skip ci]` or `[disable daily]`
3. ✅ If no skip keyword: Creates/updates `daily_updates.txt`
4. ✅ Commits with timestamp
5. ✅ Pushes to your repository

### **Sample commit it creates:**
```
Daily auto commit - 2025-10-27 17:49:09

Files changed:
- daily_updates.txt (updated with timestamp)
```

## 🕐 **Schedule Details**

- **Time**: 14:30 UTC (2:30 PM UTC)
- **Frequency**: Every single day
- **Timezone**: UTC (Universal Coordinated Time)

**Convert to your timezone:**
- PST: 6:30 AM (UTC-8)
- EST: 9:30 AM (UTC-5)
- IST: 8:00 PM (UTC+5:30)
- JST: 11:30 PM (UTC+9)

## 🔄 **Quick Actions**

### **To Stop for Today Only:**
```bash
git commit -m "Quick fix [skip ci]" --allow-empty
git push
```

### **To Stop Permanently:**
```bash
# Option 1: Comment out schedule
sed -i 's/- cron:/# - cron:/' .github/workflows/daily-commit.yml
git add .github/workflows/daily-commit.yml
git commit -m "Disable daily auto-commits"
git push

# Option 2: Delete workflow
git rm .github/workflows/daily-commit.yml
git commit -m "Remove daily auto-commit workflow"
git push
```

### **To Test Manually:**
```bash
gh workflow run daily-commit.yml
```

## 📊 **Monitoring**

### **Check if it's running:**
```bash
gh run list --workflow="daily-commit.yml" --limit 5
```

### **View latest execution:**
```bash
gh run list --limit 1
```

### **Check workflow status:**
- Visit: https://github.com/22f3001854/tds-project1-dk/actions

## ⚠️ **Important Warnings**

1. **Daily Commits**: This WILL create a commit every day
2. **Repository Growth**: Your repo will get one commit daily
3. **Git History**: Daily commits will appear in your git log
4. **Notifications**: You might get GitHub notifications for each commit

## 🎯 **Recommended Usage**

### **For Assignment Submission:**
- Keep it running until assignment deadline
- Add `[skip ci]` to regular commits to avoid interference

### **After Assignment:**
- Consider disabling or deleting the workflow
- Clean up `daily_updates.txt` if desired

### **For Testing:**
- Use manual trigger: `gh workflow run daily-commit.yml`
- Check logs: `gh run view [run-id]`

## 🔧 **Emergency Stop**

If you need to stop it RIGHT NOW:

```bash
# Quick disable via GitHub CLI
gh api repos/22f3001854/tds-project1-dk/actions/workflows/daily-commit.yml \
  --method PUT --field state=disabled

# Or delete the file
git rm .github/workflows/daily-commit.yml
git commit -m "Emergency stop auto-commits"
git push
```

---

## 📋 **Summary**

✅ **Workflow is ACTIVE** - Will commit daily at 14:30 UTC  
✅ **Control methods available** - Multiple ways to stop/control  
✅ **Skip keywords work** - Use `[skip ci]` in commit messages  
✅ **Manual override possible** - Can disable anytime  

**Current Status**: Active and scheduled for daily execution.