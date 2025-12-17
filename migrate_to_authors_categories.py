from app.models.database import engine, Author, Category, SessionLocal
from sqlalchemy import text

print("Starting migration...")

with engine.connect() as conn:
    # Step 1: Create new tables
    print("Step 1: Creating authors and categories tables...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS authors (
            id SERIAL PRIMARY KEY,
            name VARCHAR(300) NOT NULL UNIQUE,
            name_en VARCHAR(300),
            slug VARCHAR(200) NOT NULL UNIQUE,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            slug VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))
    
    # Step 2: Migrate existing authors from books table
    print("Step 2: Migrating authors...")
    conn.execute(text("""
        INSERT INTO authors (name, slug)
        SELECT DISTINCT author, author_slug
        FROM books
        WHERE author IS NOT NULL AND author_slug IS NOT NULL
        ON CONFLICT (name) DO NOTHING;
    """))
    
    # Step 3: Migrate existing categories from books table
    print("Step 3: Migrating categories...")
    conn.execute(text("""
        INSERT INTO categories (name, slug)
        SELECT DISTINCT category, 
               LOWER(REPLACE(REPLACE(category, ' ', '-'), '/', '-'))
        FROM books
        WHERE category IS NOT NULL
        ON CONFLICT (name) DO NOTHING;
    """))
    
    # Step 4: Add foreign key columns to books
    print("Step 4: Adding foreign key columns...")
    conn.execute(text("""
        ALTER TABLE books 
        ADD COLUMN IF NOT EXISTS author_id INTEGER,
        ADD COLUMN IF NOT EXISTS category_id INTEGER;
    """))
    
    # Step 5: Populate foreign keys
    print("Step 5: Populating foreign keys...")
    conn.execute(text("""
        UPDATE books 
        SET author_id = authors.id
        FROM authors
        WHERE books.author = authors.name;
    """))
    
    conn.execute(text("""
        UPDATE books 
        SET category_id = categories.id
        FROM categories
        WHERE books.category = categories.name;
    """))
    
    # Step 6: Drop old columns (optional - uncomment when ready)
    print("Step 6: Keeping old columns for now (can drop later)...")
    # conn.execute(text("ALTER TABLE books DROP COLUMN IF EXISTS author;"))
    # conn.execute(text("ALTER TABLE books DROP COLUMN IF EXISTS author_ar;"))
    # conn.execute(text("ALTER TABLE books DROP COLUMN IF EXISTS author_slug;"))
    # conn.execute(text("ALTER TABLE books DROP COLUMN IF EXISTS category;"))
    
    conn.commit()
    print("✅ Migration complete!")

# Verify migration
db = SessionLocal()
author_count = db.query(Author).count()
category_count = db.query(Category).count()
print(f"\n📊 Results:")
print(f"   Authors: {author_count}")
print(f"   Categories: {category_count}")
db.close()