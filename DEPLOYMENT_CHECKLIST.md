# Phase 3 Deployment Checklist

## Pre-Deployment Steps

### ✅ Step 1: Configure Azure App Service Environment Variables

**Choose one method:**

#### Method A: Azure Portal (Easiest)
1. Go to https://portal.azure.com
2. Navigate to **App Services** → **kitabiai-app**
3. Click **Configuration** → **Application settings**
4. Add these 5 settings:
   - `AZURE_STORAGE_CONTAINER_HTML` = `books-html`
   - `AZURE_STORAGE_CONTAINER_MARKDOWN` = `books-markdown`
   - `AZURE_STORAGE_CONTAINER_JSON` = `books-json`
   - `AZURE_STORAGE_CONTAINER_PDF` = `books-pdf`
   - `AZURE_STORAGE_CONTAINER_IMAGES` = `books-images`
5. Click **Save** → **Continue**
6. Wait ~30 seconds for app to restart

#### Method B: Azure CLI (If installed)
```powershell
# Run this script (Windows PowerShell)
.\scripts\configure_azure_env.ps1
```

Or:
```bash
# Run this script (Linux/Mac/Git Bash)
bash scripts/configure_azure_env.sh
```

---

### ⏳ Step 2: Optional - Reset Database

**Only do this if you want to start with empty database!**

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run reset script
python reset_db.py
```

Type `RESET` then `YES` to confirm.

---

### ⏳ Step 3: Optional - Test Locally First

**Recommended before deploying to production:**

```bash
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Start server
python main.py

# 3. Open browser
# Go to: http://127.0.0.1:8000

# 4. Upload a test PDF

# 5. Generate files

# 6. Verify in Azure Portal → Storage → Containers
# Files should appear in Azure Blob Storage!

# 7. Verify database
python tests/verify_upload.py
# URLs should be https:// (not file://)
```

---

## Deployment Steps

### ✅ Step 4: Commit All Changes

```bash
# Check status
git status

# Add all changes
git add .

# Commit
git commit -m "Phase 3: Complete Azure Blob Storage migration"

# Push to Phase_3 branch
git push origin Phase_3
```

---

### ✅ Step 5: Merge to Main and Deploy

```bash
# Switch to main branch
git checkout main

# Merge Phase_3
git merge Phase_3

# Push to main (this triggers CI/CD deployment)
git push origin main
```

**What happens:**
1. GitHub Actions CI/CD pipeline starts
2. Runs tests and linting
3. Builds Docker image
4. Deploys to Azure App Service
5. App restarts (~2-3 minutes total)

**Track progress:**
- Go to GitHub repository → **Actions** tab
- Watch the workflow run

---

## Post-Deployment Verification

### ✅ Step 6: Verify Deployment

1. **Check deployment completed:**
   - GitHub → Actions → Latest workflow should be ✅ green

2. **Open deployed app:**
   - Go to: `https://kitabiai-app.azurewebsites.net`
   - Or Azure Portal → App Services → kitabiai-app → **Browse**

3. **Upload a test book:**
   - Upload PDF
   - Fill metadata
   - Click "Upload and Analyze"
   - Click "💾 Generate All Files & Save to Database"

4. **Verify files in Azure Storage:**
   - Azure Portal → Storage Account "kitabiai" → Containers
   - Check:
     - ✅ `books-html` - should have HTML files
     - ✅ `books-markdown` - should have .md files
     - ✅ `books-json` - should have .jsonl files
     - ✅ `books-pdf` - should have PDF files
     - ✅ `books-images` - should have cover images (if uploaded)

5. **Verify database:**
   - Database should have book record
   - All URL fields should contain `https://` URLs (not `file://`)

---

## Final Checklist

### Pre-Deployment:
- [ ] ✅ Azure storage containers exist (all 5)
- [ ] ✅ Azure App Service env variables added
- [ ] ⏳ Database reset (optional - if you want fresh start)
- [ ] ⏳ Local testing complete (optional)

### Deployment:
- [ ] ⏳ All changes committed to Phase_3
- [ ] ⏳ Merged Phase_3 to main
- [ ] ⏳ Pushed to GitHub main
- [ ] ⏳ CI/CD pipeline completed (GitHub Actions ✅ green)

### Post-Deployment:
- [ ] ⏳ App accessible at Azure URL
- [ ] ⏳ Test upload successful
- [ ] ⏳ Files visible in Azure Blob Storage
- [ ] ⏳ Database URLs are `https://` format
- [ ] ⏳ No errors in Azure App Service logs

---

## Troubleshooting

### Issue: CI/CD pipeline fails

**Check:**
- GitHub → Actions → Failed workflow → View logs
- Look for error messages
- Common issues:
  - Linting errors → Fix code and push again
  - Test failures → Check test output
  - Docker build errors → Check Dockerfile

### Issue: App crashes after deployment

**Check Azure logs:**
```bash
# View logs in Azure Portal
# App Services → kitabiai-app → Log stream

# Or download logs
# App Services → kitabiai-app → Advanced Tools → Go → Debug console
```

**Common issues:**
- Missing environment variables → Check Configuration
- Database connection errors → Check DATABASE_URL
- Azure storage errors → Check AZURE_STORAGE_CONNECTION_STRING

### Issue: Files not uploading to Azure

**Verify:**
1. `AZURE_STORAGE_CONNECTION_STRING` is correct
2. Container names match (books-html, books-markdown, etc.)
3. Storage account has containers created
4. Check app logs for error messages

---

## Success Criteria

Your deployment is successful when:

✅ CI/CD pipeline completes without errors
✅ App loads at `https://kitabiai-app.azurewebsites.net`
✅ Can upload PDF and generate files
✅ Files appear in Azure Blob Storage containers
✅ Database records have `https://` URLs
✅ No errors in application logs

---

## Next Steps After Successful Deployment

1. **Test thoroughly:**
   - Upload multiple books
   - Test with Arabic and English PDFs
   - Verify all features work

2. **Monitor costs:**
   - Azure Portal → Cost Management
   - Track Storage, Database, App Service costs

3. **Set up monitoring:**
   - Azure Portal → App Service → Monitoring
   - Configure alerts for errors/downtime

4. **Plan backups:**
   - Database backup strategy
   - Azure Blob Storage lifecycle policies

5. **Optimize:**
   - Review performance
   - Consider CDN for files (future)
   - Optimize blob storage costs

---

## Support

If you encounter issues:

1. Check logs: Azure Portal → App Service → Log stream
2. Review documentation: `AZURE_DEPLOYMENT_GUIDE.md`
3. Verify environment variables: Azure Portal → App Service → Configuration
4. Test locally first to isolate issues

**Your app is now fully deployed on Azure!** 🎉
