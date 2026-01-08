# Phase 1 Testing Guide: Local File Storage

This guide will help you test the new local file storage feature with database URL tracking.

## What Was Implemented

### 1. **New Database Schema**
Added columns to the `books` table:
- `html_url` - URL to HTML file
- `markdown_url` - URL to Markdown file
- `pages_jsonl_url` - URL to page-level analysis JSONL
- `sections_jsonl_url` - URL to TOC sections JSONL
- `pdf_url` - URL to original PDF (for future use)
- `cover_image_url` - URL to cover image (for future use)
- `files_generated_at` - Timestamp when files were generated

### 2. **Local Storage Service**
New file: `app/services/local_storage_service.py`
- Saves files to `outputs/books/{book_id}/` folder
- Returns `file://` URLs for database storage

### 3. **Updated Generation Router**
Updated file: `app/routers/generation.py`
- `/generate/both` endpoint now saves all files and updates database
- Generates 4 files: HTML, Markdown, pages JSONL, sections JSONL
- Updates database with file URLs and timestamp

---

## Step-by-Step Testing Instructions

### **Step 0: Prerequisites**

Before starting, ensure you have:

1. **Virtual Environment Activated:**

   **Windows:**
   ```bash
   .venv\Scripts\activate
   ```

   **Linux/Mac:**
   ```bash
   source .venv/bin/activate
   ```

   You should see `(.venv)` at the beginning of your command prompt.

2. **Database Connection Configured:**

   Make sure your `.env` file has the correct `DATABASE_URL`:

   ```env
   DATABASE_URL=postgresql://user:password@host:5432/database
   ```

   **Important:** If you're using Azure PostgreSQL, ensure:
   - Your access token is valid and properly formatted
   - Your IP address is whitelisted in Azure firewall rules
   - The connection string includes all required parameters

   If you get authentication errors, you may need to refresh your Azure credentials or check your firewall settings.

---

### **Step 1: Reset Database (Create New Schema)**

Run the database reset script to create tables with the new schema:

```bash
python reset_db.py
```

**Expected Output:**
```
Dropping all existing tables...
Creating fresh tables...
✅ Tables created/updated successfully!
```

---

### **Step 2: Verify Database Schema**

Check that the new columns exist:

```bash
python tests/verify_tables.py
```

**Expected Output:**
Should show all columns including the new URL columns:
- `html_url`
- `markdown_url`
- `pages_jsonl_url`
- `sections_jsonl_url`
- `pdf_url`
- `cover_image_url`
- `files_generated_at`

---

### **Step 3: Start the Server**

```bash
python main.py
```

**Expected Output:**
```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

### **Step 4: Upload a PDF Book**

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

1. Fill in the book metadata form:
   - **Title**: e.g., "Test Book"
   - **Author**: e.g., "Test Author"
   - **Category**: e.g., "Technology"
   - **Description**: (optional)

2. Upload a PDF file (Arabic or English)

3. Click "Upload and Analyze"

**Expected Result:**
- You should see the analysis results
- The book should be saved to the database
- Check the server logs for: `"Created new book with ID: X"` or `"Updated existing book record with ID: X"`

---

### **Step 5: Generate All Files**

After upload, click the **"Generate Both (HTML + Markdown)"** button in the web interface.

Or use the API directly:
```bash
curl -X POST "http://127.0.0.1:8000/generate/both?include_toc=true&include_metadata=true"
```

**Expected Response:**
```json
{
  "ok": true,
  "message": "Generated all files and saved to local storage",
  "book_id": 1,
  "files": [
    {
      "format": "html",
      "filename": "test_book.html",
      "size_bytes": 12345,
      "url": "file:///C:/Users/Suha/Desktop/2025/bookAutomation-v3/outputs/books/1/test_book.html"
    },
    {
      "format": "markdown",
      "filename": "test_book.md",
      "size_bytes": 6789,
      "url": "file:///C:/Users/Suha/Desktop/2025/bookAutomation-v3/outputs/books/1/test_book.md"
    },
    {
      "format": "pages_jsonl",
      "filename": "test_book_pages.jsonl",
      "size_bytes": 3456,
      "url": "file:///C:/Users/Suha/Desktop/2025/bookAutomation-v3/outputs/books/1/test_book_pages.jsonl"
    },
    {
      "format": "sections_jsonl",
      "filename": "test_book_sections.jsonl",
      "size_bytes": 1234,
      "url": "file:///C:/Users/Suha/Desktop/2025/bookAutomation-v3/outputs/books/1/test_book_sections.jsonl"
    }
  ],
  "sections_count": 5,
  "files_generated_at": "2026-01-06T12:34:56.789012"
}
```

---

### **Step 6: Verify Files Were Created**

Check that files exist in the `outputs/books/` folder:

**Windows:**
```bash
dir outputs\books\1
```

**Linux/Mac:**
```bash
ls -la outputs/books/1/
```

**Expected Output:**
```
test_book.html
test_book.md
test_book_pages.jsonl
test_book_sections.jsonl
```

---

### **Step 7: Verify Database URLs**

Run the verification script to check database content:

```bash
python tests/verify_upload.py
```

**Expected Output:**
```
Total books: 1

📚 Book ID: 1
   Title: Test Book
   Author: Test Author
   Author Slug: test-author
   Category: Technology
   Language: en
   Pages: 100
   Sections: 5

   File URLs:
   - HTML: file:///C:/Users/Suha/Desktop/2025/bookAutomation-v3/outputs/books/1/test_book.html
   - Markdown: file:///C:/Users/Suha/Desktop/2025/bookAutomation-v3/outputs/books/1/test_book.md
   - Pages JSONL: file:///C:/Users/Suha/Desktop/2025/bookAutomation-v3/outputs/books/1/test_book_pages.jsonl
   - Sections JSONL: file:///C:/Users/Suha/Desktop/2025/bookAutomation-v3/outputs/books/1/test_book_sections.jsonl
   - PDF: None
   - Cover: None
   - Generated At: 2026-01-06 12:34:56.789012

👤 Authors:
   - Test Author (test-author) - 1 books

📂 Categories:
   - Technology (technology) - 1 books
```

---

### **Step 8: Test Smart Book Replacement**

Upload the **same book again** (same title + author):

1. Go back to http://127.0.0.1:8000
2. Fill in the **exact same** title and author
3. Upload the same PDF
4. Click "Upload and Analyze"
5. Generate files again

**Expected Result:**
- Server logs should show: `"Updated existing book record with ID: 1"`
- No new book record should be created
- Files should be replaced in `outputs/books/1/`
- Database URLs should be updated

Run `python tests/verify_upload.py` again - you should still see only **1 book** in the database.

---

### **Step 9: Test Different Book**

Upload a different book:

1. Use a **different title** or **different author**
2. Upload and analyze
3. Generate files

**Expected Result:**
- Server logs should show: `"Created new book with ID: 2"`
- New folder created: `outputs/books/2/`
- Run `python tests/verify_upload.py` - you should now see **2 books**

---

## Verification Checklist

- [ ] Database reset completed successfully
- [ ] New schema columns exist (verified with `verify_tables.py`)
- [ ] Book uploaded and saved to database
- [ ] All 4 files generated (HTML, Markdown, pages JSONL, sections JSONL)
- [ ] Files exist in `outputs/books/{book_id}/` folder
- [ ] Database contains correct `file://` URLs for all files
- [ ] `files_generated_at` timestamp is set
- [ ] Smart replacement works (re-uploading same book updates, doesn't duplicate)
- [ ] Different books create separate records and folders

---

## Troubleshooting

### Issue: Database Connection Errors (Azure PostgreSQL)

**Error:** `FATAL: The access token has invalid format` or `no pg_hba.conf entry for host`

**Solutions:**
1. **Refresh Azure Token**: Your Azure access token may have expired. Regenerate it using:
   ```bash
   az account get-access-token --resource https://ossrdbms-aad.database.windows.net
   ```

2. **Check IP Whitelist**: Ensure your current IP is whitelisted in Azure Portal:
   - Go to Azure Portal → PostgreSQL Server → Connection Security
   - Add your current IP address to firewall rules

3. **Verify Connection String**: Check your `.env` file has the correct format:
   ```env
   DATABASE_URL=postgresql://user:password@host.postgres.database.azure.com:5432/dbname?sslmode=require
   ```

### Issue: "No book ID available. Re-upload the PDF."
**Solution**: Upload a PDF first before generating files.

### Issue: Database schema errors
**Solution**: Run `python reset_db.py` to recreate tables.

### Issue: Files not created in `outputs/` folder
**Solution**: Check server logs for errors. Ensure write permissions exist.

### Issue: Database URLs are NULL
**Solution**: Make sure you called `/generate/both` endpoint after upload.

### Issue: Book duplicated instead of updated
**Solution**: Ensure you're using the **exact same** title and author name (case-sensitive).

### Issue: ModuleNotFoundError
**Solution**: Activate your virtual environment first (see Step 0).

---

## What to Check Before Phase 2 (Azure Migration)

Before moving to Azure Blob Storage:

1. ✅ All 4 file types generate correctly
2. ✅ Database URLs are populated correctly
3. ✅ `files_generated_at` timestamp works
4. ✅ Smart replacement works correctly
5. ✅ File paths are organized by book ID
6. ✅ JSONL content is valid (can be parsed line-by-line)

Once all these checks pass, you're ready to:
1. Reset the database one more time
2. Implement Azure Blob Storage upload
3. Replace `local_storage` with `azure_storage` service
4. Test everything again with Azure URLs

---

## Files Modified/Created

### Created:
- `app/services/local_storage_service.py` - Local file storage service
- `TESTING_PHASE1.md` - This testing guide

### Modified:
- `app/models/database.py` - Added URL columns and timestamp
- `app/routers/generation.py` - Updated to use local storage and update database
- `docs/DATABASE_DEPENDENCIES.md` - Updated schema documentation
- `SCHEMA_CHANGES.md` - Complete change log

---

## Next Steps (Phase 2)

After Phase 1 testing is complete:

1. **Create Azure Blob Storage Service** (`app/services/azure_storage_service.py`)
   - Similar interface to `local_storage_service.py`
   - Upload files to Azure Blob Storage
   - Return Azure blob URLs

2. **Update Generation Router**
   - Replace `local_storage` with `azure_storage`
   - Update database with Azure URLs instead of file:// URLs

3. **Test with Azure**
   - Verify files upload correctly
   - Verify URLs are accessible
   - Verify database contains Azure URLs
   - Test smart replacement with Azure

4. **Production Deployment**
   - Configure Azure credentials in `.env`
   - Deploy to production
   - Monitor and verify
