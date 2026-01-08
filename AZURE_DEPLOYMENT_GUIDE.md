# Azure Deployment Guide - Phase 3

## Current Status: ✅ Code Ready for Deployment

All code changes for Azure Blob Storage migration are complete. Now we need to configure Azure and deploy.

---

## Step 1: Add Environment Variables to Azure App Service

### Method A: Via Azure Portal (Recommended)

1. **Go to Azure Portal:** https://portal.azure.com

2. **Navigate to your App Service:**
   - Search for "App Services" in the top search bar
   - Click on **kitabiai-app** (your app service name)

3. **Add Environment Variables:**
   - In the left menu, click **Configuration** (under Settings)
   - Click **Application settings** tab
   - Click **+ New application setting** button

4. **Add these 5 new settings:**

   | Name | Value |
   |------|-------|
   | `AZURE_STORAGE_CONTAINER_HTML` | `books-html` |
   | `AZURE_STORAGE_CONTAINER_MARKDOWN` | `books-markdown` |
   | `AZURE_STORAGE_CONTAINER_JSON` | `books-json` |
   | `AZURE_STORAGE_CONTAINER_PDF` | `books-pdf` |
   | `AZURE_STORAGE_CONTAINER_IMAGES` | `books-images` |

   **For each setting:**
   - Click **+ New application setting**
   - Enter **Name** (e.g., `AZURE_STORAGE_CONTAINER_HTML`)
   - Enter **Value** (e.g., `books-html`)
   - Click **OK**

5. **Verify Existing Settings:**

   Make sure these settings already exist (they should):
   - ✅ `DATABASE_URL`
   - ✅ `AZURE_STORAGE_CONNECTION_STRING`
   - ✅ `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`
   - ✅ `AZURE_DOCUMENT_INTELLIGENCE_KEY`

6. **Save Changes:**
   - Click **Save** button at the top
   - Click **Continue** when prompted
   - **App will restart** (this is normal - takes ~30 seconds)

---

### Method B: Via Azure CLI (Alternative)

If you have Azure CLI installed, you can run these commands:

```bash
# Set your app name and resource group
APP_NAME="kitabiai-app"
RESOURCE_GROUP="bookautomation-insights"

# Add container name settings
az webapp config appsettings set --name $APP_NAME --resource-group $RESOURCE_GROUP --settings \
  AZURE_STORAGE_CONTAINER_HTML="books-html" \
  AZURE_STORAGE_CONTAINER_MARKDOWN="books-markdown" \
  AZURE_STORAGE_CONTAINER_JSON="books-json" \
  AZURE_STORAGE_CONTAINER_PDF="books-pdf" \
  AZURE_STORAGE_CONTAINER_IMAGES="books-images"
```

---

## Step 2: Reset Azure Database (Optional - Fresh Start)

### If You Want to Start with Empty Database:

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run reset script
python reset_db.py
```

**The script will:**
1. Show current database statistics (4 books, X sections, etc.)
2. Ask you to type `RESET` to confirm
3. Ask you to type `YES` to double-confirm
4. Drop all tables
5. Recreate empty tables with the new schema (including all URL columns)

**WARNING:** This permanently deletes all data! Only do this if you want to start fresh.

---

## Step 3: Deploy to Azure

### Option 1: Deploy via Git (Automatic CI/CD)

Your CI/CD pipeline is already configured! Just push to main:

```bash
# 1. Make sure all changes are committed on Phase_3 branch
git status
git add .
git commit -m "Phase 3: Complete Azure Blob Storage migration"
git push origin Phase_3

# 2. Merge to main and push (this triggers deployment)
git checkout main
git merge Phase_3
git push origin main
```

**What happens next:**
1. GitHub Actions CI/CD pipeline starts automatically
2. Runs linting and tests
3. Builds Docker image
4. Deploys to Azure App Service
5. Your app restarts with new code (~2-3 minutes total)

**Track deployment progress:**
- Go to your GitHub repository
- Click **Actions** tab
- Watch the deployment workflow

---

### Option 2: Manual Testing First (Recommended)

Test locally before deploying to production:

```bash
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. (Optional) Reset database
python reset_db.py

# 3. Start server locally
python main.py

# 4. Open browser: http://127.0.0.1:8000

# 5. Upload a test PDF with cover image

# 6. Click "Generate All Files & Save to Database"

# 7. Verify in Azure Portal:
#    - Go to Storage Account "kitabiai" → Containers
#    - Check each container (books-html, books-markdown, etc.)
#    - You should see files uploaded!

# 8. Verify database:
python tests/verify_upload.py
#    URLs should now be https:// (not file://)
```

**If local testing works, deploy to Azure:**
```bash
git checkout main
git merge Phase_3
git push origin main
```

---

## Step 4: Verify Deployment

### After Deployment Completes:

1. **Check Azure App Service:**
   - Go to Azure Portal → App Services → kitabiai-app
   - Click **Browse** to open your deployed app
   - URL should be: `https://kitabiai-app.azurewebsites.net`

2. **Upload a Test Book:**
   - Upload a PDF
   - Fill in metadata
   - Click "Upload and Analyze"
   - Click "Generate All Files & Save to Database"

3. **Verify Files in Azure Storage:**
   - Go to Azure Portal → Storage Account "kitabiai" → Containers
   - Check each container - should see files uploaded

4. **Verify Database:**
   - Files should have `https://` URLs (not `file://`)
   - All 6 file types should be stored

---

## Complete Deployment Checklist

### Pre-Deployment:

- [x] ✅ Azure storage containers created
- [x] ✅ Code updated to use `azure_storage`
- [x] ✅ `requirements.txt` includes `azure-storage-blob`
- [x] ✅ `.env` configured with container names
- [ ] ⏳ **Azure App Service environment variables added** ← DO THIS FIRST
- [ ] ⏳ Database reset (optional)

### Deployment:

- [ ] ⏳ Local testing complete (optional but recommended)
- [ ] ⏳ Committed all changes to Phase_3 branch
- [ ] ⏳ Merged Phase_3 to main
- [ ] ⏳ Pushed to GitHub main branch
- [ ] ⏳ CI/CD pipeline completed successfully

### Post-Deployment:

- [ ] ⏳ Deployed app accessible at Azure URL
- [ ] ⏳ Test upload works
- [ ] ⏳ Files appear in Azure Blob Storage
- [ ] ⏳ Database URLs are `https://` (not `file://`)

---

## Troubleshooting

### Issue: App crashes after deployment

**Check:** Environment variables in Azure App Service
- Go to Azure Portal → App Service → Configuration
- Verify all required variables are set
- Check logs: Azure Portal → App Service → Log stream

### Issue: Files not uploading to Azure

**Check:** `AZURE_STORAGE_CONNECTION_STRING` is set correctly
- Go to Storage Account → Access keys
- Copy connection string
- Update in App Service → Configuration

### Issue: Database connection fails

**Check:** Database connection string
- Verify `DATABASE_URL` in App Service settings
- Check firewall rules allow Azure services
- Verify IP whitelist includes Azure App Service

---

## Next Steps After Deployment

1. ✅ Test thoroughly with real books
2. ✅ Monitor Azure costs (Storage + Database + App Service)
3. ✅ Set up backup strategy for database
4. ✅ Consider CDN for serving static files (future optimization)
5. ✅ Set up monitoring and alerts

---

## Summary

**To complete deployment:**

1. **Add 5 environment variables to Azure App Service** (Step 1)
2. **Optional:** Reset database for fresh start (Step 2)
3. **Deploy:** Merge Phase_3 to main and push (Step 3)
4. **Verify:** Test deployed app (Step 4)

**After deployment, everything runs in Azure:**
- ✅ App Service (code)
- ✅ PostgreSQL (database)
- ✅ Blob Storage (files)
- ✅ Document Intelligence (Arabic PDFs)

**Your app is now fully cloud-native!** 🚀
