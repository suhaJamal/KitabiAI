# Database Schema Changes - Azure File Storage Support

## Date: 2026-01-06

## Summary
Updated the Book table schema to support Azure Blob Storage URLs for all generated and source files, replacing the single `json_url` column with separate URLs for each file type.

---

## Changes Made

### 1. **Removed:**
- `json_url` (String(500)) - Single JSON URL column

### 2. **Added - Generated File URLs:**
- `pages_jsonl_url` (String(500)) - URL to page-level analysis JSONL file
- `sections_jsonl_url` (String(500)) - URL to TOC sections JSONL file

### 3. **Added - Source File URLs:**
- `pdf_url` (String(500)) - URL to original PDF in Azure Blob Storage
- `cover_image_url` (String(500)) - URL to book cover image

### 4. **Added - Timestamp:**
- `files_generated_at` (DateTime) - Timestamp when HTML/Markdown/JSON files were generated
  - Replaces the need for separate timestamps for each file type
  - All files are generated together, so one timestamp is sufficient

---

## Rationale

### Why Two JSONL URLs?
The system generates TWO different JSONL files with different purposes:
1. **`_pages.jsonl`** (→ `pages_jsonl_url`) - Page-level analysis with text content
2. **`_sections.jsonl`** (→ `sections_jsonl_url`) - TOC sections with metadata

### Why PDF and Cover URLs?
- **`pdf_url`**: Store original PDF in Azure for direct access/download
- **`cover_image_url`**: Store book cover (extracted from first page or uploaded separately) for display in the library interface

### Why One Timestamp?
- All files (HTML, Markdown, pages JSONL, sections JSONL) are generated in a single operation
- Simplifies schema and reduces redundancy
- Still allows tracking when files were last regenerated

---

## File URL Columns Summary

| Column Name | Purpose | Example Value |
|-------------|---------|---------------|
| `html_url` | HTML book version | `https://storage.azure.com/books/123/book.html` |
| `markdown_url` | Markdown book version | `https://storage.azure.com/books/123/book.md` |
| `pages_jsonl_url` | Page-level JSONL | `https://storage.azure.com/books/123/pages.jsonl` |
| `sections_jsonl_url` | TOC sections JSONL | `https://storage.azure.com/books/123/sections.jsonl` |
| `pdf_url` | Original PDF | `https://storage.azure.com/books/123/original.pdf` |
| `cover_image_url` | Book cover image | `https://storage.azure.com/books/123/cover.jpg` |

---

## Migration Notes

### For Existing Data:
If you have existing books in the database, you'll need to:
1. Run `reset_db.py` to recreate tables with new schema (development only)
2. For production, create a migration script to:
   - Add new columns
   - Migrate existing `json_url` values if any
   - Set `files_generated_at` based on `updated_at` or `created_at`

### New Books:
- All URL columns will be `NULL` initially
- After generating files and uploading to Azure, populate these columns
- Set `files_generated_at` to current timestamp when files are generated

---

## Next Steps

### Required Updates:

1. **`app/routers/generation.py`**
   - After uploading files to Azure, populate the URL columns
   - Set `files_generated_at` timestamp
   - Example:
     ```python
     book.html_url = azure_html_url
     book.markdown_url = azure_markdown_url
     book.pages_jsonl_url = azure_pages_jsonl_url
     book.sections_jsonl_url = azure_sections_jsonl_url
     book.files_generated_at = datetime.utcnow()
     db.commit()
     ```

2. **`app/routers/upload.py`** (if storing PDF immediately)
   - After uploading PDF to Azure, populate `pdf_url`
   - If extracting cover image, populate `cover_image_url`

3. **Azure Blob Storage Service**
   - Create a service to upload files to Azure Blob Storage
   - Return the public URLs for storage in database

4. **Tests**
   - Update `tests/verify_tables.py` to check for new columns
   - Update `tests/verify_upload.py` if testing Azure uploads

---

## Database Structure (Full Book Table)

```python
class Book(Base):
    __tablename__ = "books"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Book information
    title = Column(String(500), nullable=False)
    title_ar = Column(String(500))
    author_id = Column(Integer, ForeignKey('authors.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    language = Column(String(2), nullable=False)  # "ar" or "en"
    description = Column(Text)
    keywords = Column(String(500))
    publication_date = Column(String(50))
    isbn = Column(String(20))
    page_count = Column(Integer)
    section_count = Column(Integer)

    # Generated file URLs (Azure Blob Storage)
    html_url = Column(String(500))
    markdown_url = Column(String(500))
    pages_jsonl_url = Column(String(500))
    sections_jsonl_url = Column(String(500))

    # Source file URLs (Azure Blob Storage)
    pdf_url = Column(String(500))
    cover_image_url = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    files_generated_at = Column(DateTime)

    # Other
    view_count = Column(Integer, default=0)
    status = Column(String(20), default='published')

    # Relationships
    author = relationship("Author", back_populates="books")
    category_rel = relationship("Category", back_populates="books")
    sections = relationship("Section", back_populates="book", cascade="all, delete-orphan")
```

---

## References

- **Schema Definition**: [app/models/database.py](app/models/database.py) (lines 42-82)
- **Dependencies Guide**: [docs/DATABASE_DEPENDENCIES.md](docs/DATABASE_DEPENDENCIES.md)
- **Reset Script**: [reset_db.py](reset_db.py)
