# Database Dependencies Reference

This document lists all Python files that interact with the database and would need updates when you modify the database schema (add/remove columns, tables, or relationships).

## 🔴 Critical Files - ALWAYS Update

### 1. `app/models/database.py` ⚠️ **MOST IMPORTANT**
**Purpose**: Defines the database schema using SQLAlchemy ORM models

**What to update**:
- `Book` class: When adding/removing book table columns
- `Section` class: When adding/removing section table columns
- `Author` class: When adding/removing author table columns
- `Category` class: When adding/removing category table columns
- Relationships: When changing foreign keys or relationships between tables

**Example changes needed**:
```python
# Adding a new column to Book table
class Book(Base):
    # ... existing columns ...
    publisher = Column(String(200))  # NEW COLUMN
    edition = Column(Integer)         # NEW COLUMN
```

---

### 2. `app/routers/upload.py`
**Purpose**: Handles PDF upload, metadata processing, and database insertion

**What to update**:
- **Form parameters** (lines 71-84): Add new Form() fields for new columns
- **Metadata object creation** (lines 109-119): Update BookMetadata construction if adding metadata fields
- **Book record creation** (lines 227-239): Add new columns when creating `Book()` object
- **Book record update** (lines 213-221): Add new columns when updating existing book
- **Section creation** (lines 248-257): Add new columns when creating `Section()` objects

**Example changes needed**:
```python
# If adding "publisher" column to Book table:

# 1. Add form parameter
publisher: str = Form(None),  # Optional - Publisher name

# 2. Update Book creation
new_book = Book(
    # ... existing fields ...
    publisher=publisher,  # NEW FIELD
)

# 3. Update existing book
existing_book.publisher = publisher  # NEW FIELD
```

---

### 3. `app/models/schemas.py`
**Purpose**: Pydantic models for request/response validation

**What to update**:
- **BookMetadata class** (lines 35-61): Add new fields that users can provide
- **BookInfo class** (lines 63-75): Add new fields for API responses
- **SectionInfo class** (lines 23-28): If adding section-level fields

**Example changes needed**:
```python
# Adding publisher to metadata
class BookMetadata(BaseModel):
    # ... existing fields ...
    publisher: Optional[str] = Field(None, description="Publisher name")
```

---

## 🟡 Important Files - Update If Relevant

### 4. `app/routers/generation.py`
**Purpose**: Handles markdown/HTML generation and export

**What to update**:
- Database queries if you add new columns that should be included in exports
- Metadata serialization for generated files

**When to update**: Only if new columns should appear in generated HTML/Markdown files

---

### 5. `app/services/export_service.py`
**Purpose**: Exports data to JSONL format

**What to update**:
- JSONL export format if new columns should be included in exports
- Data serialization logic

**When to update**: Only if new columns should appear in JSONL exports

---

## 🟢 Utility Scripts - Update for Migrations

### 6. `reset_db.py`
**Purpose**: Drops and recreates all database tables

**What to update**: Usually nothing (automatically uses models from database.py)

**Note**: This script will automatically pick up schema changes since it uses `Base.metadata.drop_all()` and `Base.metadata.create_all()`

---

### 7. `scripts/migrate_to_authors_categories.py`
**Purpose**: Migration script (converts old author/category strings to foreign keys)

**What to update**: Only relevant for one-time migrations. Create similar scripts for future schema changes.

---

### 8. `scripts/add_author_slug.py`
**Purpose**: Migration script (adds slug field to authors)

**What to update**: Only relevant for one-time migrations. Create similar scripts for future schema changes.

---

## 🔵 Test Files - Update for Validation

### 9. `tests/verify_tables.py`
**Purpose**: Verifies database tables exist and have correct structure

**What to update**:
- Add new table names to verification checks
- Add new column names to validation

---

### 10. `tests/verify_upload.py`
**Purpose**: Tests the upload functionality

**What to update**:
- Test data if new required fields are added
- Assertions if checking for new fields in responses

---

## 📊 Current Database Schema (Book Table)

### Metadata Columns:
- `id` - Primary key
- `title` - Book title (required)
- `title_ar` - Arabic title (optional)
- `author_id` - Foreign key to Authors table (required)
- `category_id` - Foreign key to Categories table (optional)
- `language` - Language code: "ar" or "en" (required)
- `description` - Book description (optional)
- `keywords` - Comma-separated keywords (optional)
- `publication_date` - Publication date (optional)
- `isbn` - ISBN number (optional)
- `page_count` - Total page count
- `section_count` - Number of TOC sections

### Generated File URLs:
- `html_url` - Azure URL to HTML version
- `markdown_url` - Azure URL to Markdown version
- `pages_jsonl_url` - Azure URL to page-level analysis JSONL
- `sections_jsonl_url` - Azure URL to TOC sections JSONL

### Source File URLs:
- `pdf_url` - Azure URL to original PDF
- `cover_image_url` - Azure URL to book cover image

### Timestamps:
- `created_at` - When book was first uploaded
- `updated_at` - Last modification time (auto-updated)
- `files_generated_at` - When HTML/Markdown/JSON files were generated

### Other:
- `view_count` - Number of views (default: 0)
- `status` - Publication status (default: 'published')

---

## 📋 Database Change Checklist

When adding a new column (e.g., "publisher" to Book table):

- [ ] **Step 1**: Update `app/models/database.py` - Add column to model class
- [ ] **Step 2**: Update `app/models/schemas.py` - Add field to Pydantic models
- [ ] **Step 3**: Update `app/routers/upload.py` - Add form parameter and database operations
- [ ] **Step 4**: Update `app/ui/template.py` - Add form field to HTML (if user-facing)
- [ ] **Step 5**: Run `reset_db.py` to recreate tables (development only)
- [ ] **Step 6**: Update tests (`tests/verify_tables.py`, `tests/verify_upload.py`)
- [ ] **Step 7**: Update exports if needed (`app/routers/generation.py`, `app/services/export_service.py`)

---

## 📋 Database Change Checklist (Adding New Table)

When adding a completely new table (e.g., "Publishers"):

- [ ] **Step 1**: Update `app/models/database.py` - Create new model class
- [ ] **Step 2**: Update `app/models/schemas.py` - Create Pydantic model if needed
- [ ] **Step 3**: Update `app/routers/upload.py` - Add CRUD operations
- [ ] **Step 4**: Update `app/ui/template.py` - Add UI if needed
- [ ] **Step 5**: Run `reset_db.py` to create new table
- [ ] **Step 6**: Create migration script if converting from existing data
- [ ] **Step 7**: Update tests

---

## 🚨 Files That DON'T Need Updates

These files do NOT interact with the database and won't need changes:

- `app/services/language_detector.py` - Language detection only
- `app/services/pdf_analyzer.py` - PDF analysis only
- `app/services/arabic_toc_extractor.py` - TOC extraction only
- `app/services/english_toc_extractor.py` - TOC extraction only
- `app/services/ocr_detector.py` - OCR detection only
- `app/services/html_generator.py` - HTML generation (uses schemas, not DB directly)
- `app/services/markdown_generator.py` - Markdown generation (uses schemas, not DB directly)
- `app/core/config.py` - Configuration only
- `app/core/logging.py` - Logging configuration only

---

## 📝 Quick Reference Table

| File | Type | Update When | Priority |
|------|------|-------------|----------|
| `app/models/database.py` | Schema Definition | Adding/removing columns or tables | 🔴 Critical |
| `app/routers/upload.py` | CRUD Operations | Adding/removing any field | 🔴 Critical |
| `app/models/schemas.py` | API Models | Adding/removing API fields | 🔴 Critical |
| `app/routers/generation.py` | Export Logic | New fields should appear in exports | 🟡 Important |
| `app/services/export_service.py` | JSONL Export | New fields should appear in JSONL | 🟡 Important |
| `reset_db.py` | DB Reset | Usually auto-updates | 🟢 Automatic |
| `tests/verify_tables.py` | Table Tests | Adding/removing tables/columns | 🔵 Testing |
| `tests/verify_upload.py` | Upload Tests | Changing upload behavior | 🔵 Testing |

---

## 💡 Pro Tips

1. **Always start with `database.py`**: This is the source of truth for your schema
2. **Use migrations for production**: Don't use `reset_db.py` in production - create migration scripts
3. **Test locally first**: Use `reset_db.py` to test schema changes before deploying
4. **Update Pydantic models**: Keep `schemas.py` in sync with `database.py` for proper validation
5. **Don't forget the UI**: If adding user-facing fields, update `template.py` form
6. **Check exports**: Decide if new fields should appear in HTML/Markdown/JSONL exports

---

## 📞 Need Help?

If unsure whether a file needs updating:
1. Search for the table name (e.g., `Book`, `Section`, `Author`, `Category`)
2. Search for `db.query` or `SessionLocal` to find database operations
3. Check this document for guidance
