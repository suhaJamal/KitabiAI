"""
Database Reset Script

This script will:
1. Drop all existing tables (books, sections, authors, categories)
2. Recreate all tables with a clean schema
3. Start with an empty database

DANGER: This will permanently delete ALL data in the database!
Use with caution - only for development/testing.

Usage:
    python reset_db.py
"""

import sys
from app.models.database import Base, engine, SessionLocal
from sqlalchemy import inspect


def confirm_reset():
    """Ask user to confirm before proceeding with database reset."""
    print("\n" + "="*70)
    print("⚠️  DATABASE RESET - DANGER ZONE ⚠️")
    print("="*70)
    print("\nThis will PERMANENTLY DELETE all data in the database:")
    print("  • All books")
    print("  • All sections (TOC entries)")
    print("  • All authors")
    print("  • All categories")
    print("\nThis action CANNOT be undone!\n")

    response = input("Type 'RESET' (in capital letters) to confirm: ").strip()

    if response != "RESET":
        print("\n❌ Reset cancelled. Database was not modified.")
        return False

    # Double confirmation
    response2 = input("\nAre you absolutely sure? Type 'YES' to proceed: ").strip()

    if response2 != "YES":
        print("\n❌ Reset cancelled. Database was not modified.")
        return False

    return True


def show_current_stats():
    """Show current database statistics before reset."""
    try:
        db = SessionLocal()

        # Import models
        from app.models.database import Book, Section, Author, Category

        book_count = db.query(Book).count()
        section_count = db.query(Section).count()
        author_count = db.query(Author).count()
        category_count = db.query(Category).count()

        print("\n📊 Current Database Statistics:")
        print(f"  • Books: {book_count}")
        print(f"  • Sections: {section_count}")
        print(f"  • Authors: {author_count}")
        print(f"  • Categories: {category_count}")

        db.close()

        return book_count + section_count + author_count + category_count > 0

    except Exception as e:
        print(f"\n⚠️  Could not retrieve database stats: {e}")
        return True  # Assume data exists


def reset_database():
    """Drop all tables and recreate them."""

    print("\n🔄 Starting database reset...\n")

    # Step 1: Show what tables exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if existing_tables:
        print(f"📋 Found {len(existing_tables)} existing table(s): {', '.join(existing_tables)}")
    else:
        print("📋 No existing tables found.")

    # Step 2: Drop all tables
    try:
        print("\n🗑️  Dropping all tables...")
        Base.metadata.drop_all(engine)
        print("✅ All tables dropped successfully!")
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        sys.exit(1)

    # Step 3: Recreate all tables
    try:
        print("\n🏗️  Creating fresh tables...")
        Base.metadata.create_all(engine)
        print("✅ All tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

    # Step 4: Verify the reset
    inspector = inspect(engine)
    new_tables = inspector.get_table_names()

    print(f"\n📋 New table(s) created: {', '.join(new_tables)}")

    print("\n" + "="*70)
    print("✅ DATABASE RESET COMPLETE!")
    print("="*70)
    print("\nYour database is now empty and ready for fresh data.")
    print("You can now upload books through the web interface.\n")


def main():
    """Main function to orchestrate database reset."""

    print("\n" + "="*70)
    print("Database Reset Utility")
    print("="*70)

    # Show current database statistics
    has_data = show_current_stats()

    if not has_data:
        print("\n💡 Database appears to be empty. Reset may not be necessary.")
        response = input("\nDo you still want to proceed? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("\n❌ Reset cancelled.")
            return

    # Ask for confirmation
    if not confirm_reset():
        return

    # Perform the reset
    reset_database()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Reset cancelled by user (Ctrl+C).")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
