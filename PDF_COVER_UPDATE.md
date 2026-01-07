# PDF & Cover Image Upload Feature

## What Was Added

Added functionality to save the uploaded PDF file and optional book cover image to local storage and database.

---

## Changes Made

### 1. **Upload Router** ([app/routers/upload.py](app/routers/upload.py))

**Line 84**: Added cover_image parameter
```python
cover_image: UploadFile = File(None),  # Optional - Book cover image
```

**Lines 280-305**: Added code to save PDF and cover image after book creation
- Saves PDF file to `outputs/books/{book_id}/{filename}.pdf`
- Saves cover image (if provided) to `outputs/books/{book_id}/cover.{ext}`
- Updates database with `pdf_url` and `cover_image_url`

### 2. **Upload Form** ([app/ui/template.py](app/ui/template.py:689-698))

Added cover image upload field:
```html
<!-- Cover Image Upload Section (Optional) -->
<div class="form-section">
  <label>
    🖼️ Book Cover Image (Optional)
  </label>
  <input name="cover_image" type="file" accept="image/*" />
  <p>Upload a cover image (JPG, PNG, etc.)...</p>
</div>
```

---

## How It Works

### Upload Flow:

1. **User uploads PDF + optional cover image**
2. **PDF is analyzed** (language detection, TOC extraction)
3. **Book saved to database** (metadata, sections)
4. **PDF saved locally**: `outputs/books/{book_id}/filename.pdf`
5. **Cover saved locally** (if provided): `outputs/books/{book_id}/cover.jpg`
6. **Database updated** with `pdf_url` and `cover_image_url`

### File Structure:
```
outputs/books/1/
  ├── book.pdf              (original PDF)
  ├── cover.jpg             (cover image, if uploaded)
  ├── book.html             (generated later)
  ├── book.md               (generated later)
  ├── book_pages.jsonl      (generated later)
  └── book_sections.jsonl   (generated later)
```

---

## Testing

### Test 1: Upload PDF Only

1. Restart server: `python main.py`
2. Go to http://127.0.0.1:8000
3. Upload a PDF (don't select cover image)
4. Fill in metadata
5. Click "Upload and Analyze"
6. Run `python tests/verify_upload.py`

**Expected:**
```
📁 File URLs:
   - PDF: file:///C:/Users/Suha/.../outputs/books/1/filename.pdf
   - Cover: Not uploaded
```

### Test 2: Upload PDF + Cover Image

1. Upload a PDF
2. **Select a cover image** (JPG, PNG, etc.)
3. Fill in metadata
4. Click "Upload and Analyze"
5. Run `python tests/verify_upload.py`

**Expected:**
```
📁 File URLs:
   - PDF: file:///C:/Users/Suha/.../outputs/books/1/filename.pdf
   - Cover: file:///C:/Users/Suha/.../outputs/books/1/cover.jpg
```

### Test 3: Verify Files Exist

```bash
# Check that both files were created
dir outputs\books\1
```

**Expected:**
```
la-tahzan.pdf
cover.jpg
```

---

## Complete Workflow Test

1. **Reset database**: `python reset_db.py`
2. **Start server**: `python main.py`
3. **Upload PDF + cover**:
   - Select PDF file
   - Select cover image (JPG/PNG)
   - Fill in title, author, etc.
   - Upload

4. **Generate all files**:
   - Click green button: "💾 Generate All Files & Save to Database"

5. **Verify everything**:
   ```bash
   python tests/verify_upload.py
   ```

**Expected Database Output:**
```
📚 Book ID: 1
   Title: Your Book
   Author: Your Author
   Pages: 584
   Sections: 347

   📁 File URLs:
   - HTML: file:///.../outputs/books/1/book.html
   - Markdown: file:///.../outputs/books/1/book.md
   - Pages JSONL: file:///.../outputs/books/1/book_pages.jsonl
   - Sections JSONL: file:///.../outputs/books/1/book_sections.jsonl
   - PDF: file:///.../outputs/books/1/book.pdf
   - Cover: file:///.../outputs/books/1/cover.jpg
   - Generated At: 2026-01-06 17:30:00
```

**Expected Files:**
```
outputs/books/1/
  ├── book.pdf              ✅
  ├── cover.jpg             ✅
  ├── book.html             ✅
  ├── book.md               ✅
  ├── book_pages.jsonl      ✅
  └── book_sections.jsonl   ✅
```

---

## Benefits

1. **Complete Local Storage**: All files (PDF, cover, generated files) in one place
2. **Database Tracking**: All file URLs stored in database
3. **Easy Migration**: Just swap local_storage for azure_storage later
4. **Cover Image Support**: Can display book covers in library interface
5. **Organized Structure**: Each book has its own folder

---

## Next Steps for Phase 2 (Azure)

When migrating to Azure:
1. Create `azure_storage_service.py` with same interface as `local_storage_service.py`
2. Replace imports in upload.py and generation.py
3. All file URLs will be Azure blob URLs instead of file:// URLs
4. Everything else stays the same!
