# Quick Testing Guide - Phase 1

## Quick Start (5 Minutes)

### 0. Activate Virtual Environment (Important!)
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 1. Reset Database
```bash
python reset_db.py
```

### 2. Start Server
```bash
python main.py
```

### 3. Test in Browser
1. Open: http://127.0.0.1:8000
2. Fill form: Title="Test Book", Author="Test Author"
3. Upload a PDF
4. Click "Generate Both (HTML + Markdown)"

### 4. Verify Results
```bash
# Check database
python tests/verify_upload.py

# Check files
dir outputs\books\1         # Windows
ls outputs/books/1/         # Linux/Mac
```

---

## Expected Results

### Files Created:
```
outputs/books/1/
  ├── test_book.html
  ├── test_book.md
  ├── test_book_pages.jsonl
  └── test_book_sections.jsonl
```

### Database Content:
- Book record with ID=1
- 4 file URLs (all starting with `file:///`)
- `files_generated_at` timestamp set
- Author and Category created automatically

---

## Test Smart Replacement

Upload the **same book again** (same title + author):
- Should update existing record (ID still = 1)
- Should replace files in `outputs/books/1/`
- Should NOT create book with ID=2

---

## Common Issues

**"No book ID available"** → Upload PDF first

**Schema errors** → Run `python reset_db.py`

**Files not created** → Check `outputs/books/` folder exists

**URLs are NULL** → Did you click "Generate Both"?

---

For detailed testing instructions, see [TESTING_PHASE1.md](TESTING_PHASE1.md)
