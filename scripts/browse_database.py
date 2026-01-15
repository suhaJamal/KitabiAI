"""
Database Browser Script
Displays all tables, columns, and record counts in the database.
"""

import os
import sys
from pathlib import Path

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text
from app.models.database import engine, SessionLocal

def browse_database():
    """Browse all tables in the database and display their structure."""

    print("=" * 70)
    print("📊 DATABASE BROWSER - KitabiAI")
    print("=" * 70)

    # Get inspector
    inspector = inspect(engine)

    # Get all table names
    tables = inspector.get_table_names()

    print(f"\n📁 Found {len(tables)} tables in database\n")

    # Create session for counting records
    db = SessionLocal()

    total_records = 0

    for table_name in sorted(tables):
        print("-" * 70)
        print(f"📋 TABLE: {table_name}")
        print("-" * 70)

        # Get columns
        columns = inspector.get_columns(table_name)

        # Get record count
        try:
            result = db.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            count = result.scalar()
            total_records += count
        except Exception as e:
            count = f"Error: {e}"

        print(f"   Records: {count}")
        print(f"   Columns: {len(columns)}")
        print()

        # Display columns
        print("   | # | Column Name          | Type              | Nullable | Default |")
        print("   |---|----------------------|-------------------|----------|---------|")

        for i, col in enumerate(columns, 1):
            col_name = col['name'][:20].ljust(20)
            col_type = str(col['type'])[:17].ljust(17)
            nullable = "Yes" if col.get('nullable', True) else "No"
            default = str(col.get('default', ''))[:7] if col.get('default') else ''

            print(f"   | {i:<1} | {col_name} | {col_type} | {nullable:<8} | {default:<7} |")

        # Get primary keys
        pk = inspector.get_pk_constraint(table_name)
        if pk and pk.get('constrained_columns'):
            print(f"\n   🔑 Primary Key: {', '.join(pk['constrained_columns'])}")

        # Get foreign keys
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            print(f"   🔗 Foreign Keys:")
            for fk in fks:
                cols = ', '.join(fk['constrained_columns'])
                ref_table = fk['referred_table']
                ref_cols = ', '.join(fk['referred_columns'])
                print(f"      - {cols} → {ref_table}({ref_cols})")

        # Get indexes
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print(f"   📇 Indexes:")
            for idx in indexes:
                idx_name = idx['name']
                idx_cols = ', '.join(idx['column_names'])
                unique = " (UNIQUE)" if idx.get('unique') else ""
                print(f"      - {idx_name}: {idx_cols}{unique}")

        print()

    # Summary
    print("=" * 70)
    print("📈 SUMMARY")
    print("=" * 70)
    print(f"   Total Tables: {len(tables)}")
    print(f"   Total Records: {total_records:,}")
    print()

    # Show sample data from key tables
    print("=" * 70)
    print("📖 SAMPLE DATA")
    print("=" * 70)

    # Sample books
    print("\n📚 Recent Books (last 5):")
    try:
        result = db.execute(text('''
            SELECT b.id, b.title, a.name as author, b.language, b.page_count
            FROM books b
            LEFT JOIN authors a ON b.author_id = a.id
            ORDER BY b.id DESC
            LIMIT 5
        '''))
        rows = result.fetchall()
        if rows:
            print("   | ID | Title                                    | Author              | Lang | Pages |")
            print("   |----|------------------------------------------|---------------------|------|-------|")
            for row in rows:
                title = (row[1] or '')[:40].ljust(40)
                author = (row[2] or '')[:19].ljust(19)
                lang = (row[3] or '')[:4].ljust(4)
                pages = str(row[4] or 0)
                print(f"   | {row[0]:<2} | {title} | {author} | {lang} | {pages:<5} |")
        else:
            print("   (No books found)")
    except Exception as e:
        print(f"   Error: {e}")

    # Sample authors
    print("\n👤 Authors:")
    try:
        result = db.execute(text('''
            SELECT a.id, a.name, a.name_en, COUNT(b.id) as book_count
            FROM authors a
            LEFT JOIN books b ON a.id = b.author_id
            GROUP BY a.id, a.name, a.name_en
            ORDER BY book_count DESC
            LIMIT 5
        '''))
        rows = result.fetchall()
        if rows:
            print("   | ID | Name (Arabic)                  | Name (English)       | Books |")
            print("   |----|--------------------------------|----------------------|-------|")
            for row in rows:
                name_ar = (row[1] or '')[:30].ljust(30)
                name_en = (row[2] or '')[:20].ljust(20)
                print(f"   | {row[0]:<2} | {name_ar} | {name_en} | {row[3]:<5} |")
        else:
            print("   (No authors found)")
    except Exception as e:
        print(f"   Error: {e}")

    # Sample categories
    print("\n📂 Categories:")
    try:
        result = db.execute(text('''
            SELECT c.id, c.name, c.slug, COUNT(bc.book_id) as book_count
            FROM categories c
            LEFT JOIN book_categories bc ON c.id = bc.category_id
            GROUP BY c.id, c.name, c.slug
            ORDER BY book_count DESC
            LIMIT 10
        '''))
        rows = result.fetchall()
        if rows:
            print("   | ID | Category Name                  | Slug                 | Books |")
            print("   |----|--------------------------------|----------------------|-------|")
            for row in rows:
                name = (row[1] or '')[:30].ljust(30)
                slug = (row[2] or '')[:20].ljust(20)
                print(f"   | {row[0]:<2} | {name} | {slug} | {row[3]:<5} |")
        else:
            print("   (No categories found)")
    except Exception as e:
        print(f"   Error: {e}")

    # Pages summary
    print("\n📄 Pages Summary:")
    try:
        result = db.execute(text('''
            SELECT
                COUNT(*) as total_pages,
                SUM(word_count) as total_words,
                SUM(char_count) as total_chars,
                AVG(word_count) as avg_words_per_page
            FROM pages
        '''))
        row = result.fetchone()
        if row and row[0]:
            print(f"   Total Pages: {row[0]:,}")
            print(f"   Total Words: {row[1]:,}" if row[1] else "   Total Words: N/A")
            print(f"   Total Characters: {row[2]:,}" if row[2] else "   Total Characters: N/A")
            print(f"   Avg Words/Page: {row[3]:.1f}" if row[3] else "   Avg Words/Page: N/A")
        else:
            print("   (No pages found)")
    except Exception as e:
        print(f"   Error: {e}")

    # Language distribution
    print("\n🌍 Language Distribution:")
    try:
        result = db.execute(text('''
            SELECT language, COUNT(*) as count
            FROM books
            GROUP BY language
            ORDER BY count DESC
        '''))
        rows = result.fetchall()
        if rows:
            for row in rows:
                lang = row[0] or 'Unknown'
                print(f"   - {lang}: {row[1]} books")
        else:
            print("   (No data)")
    except Exception as e:
        print(f"   Error: {e}")

    db.close()

    print("\n" + "=" * 70)
    print("✅ Database browse complete!")
    print("=" * 70)


if __name__ == "__main__":
    browse_database()