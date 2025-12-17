# verify_upload.py
from app.models.database import SessionLocal, Book, Section, Author, Category

db = SessionLocal()

# Check books
books = db.query(Book).all()
print(f"Total books: {len(books)}")

for book in books:
    print(f"\n📚 Book ID: {book.id}")
    print(f"   Title: {book.title}")
    print(f"   Author: {book.author.name}")
    print(f"   Author Slug: {book.author.slug}")
    print(f"   Category: {book.category_rel.name if book.category_rel else 'None'}")
    print(f"   Language: {book.language}")
    print(f"   Pages: {book.page_count}")
    
    # Check sections
    sections_count = db.query(Section).filter(Section.book_id == book.id).count()
    print(f"   Sections: {sections_count}")

# Show all authors
print("\n👤 Authors:")
authors = db.query(Author).all()
for author in authors:
    book_count = len(author.books)
    print(f"   - {author.name} ({author.slug}) - {book_count} books")

# Show all categories
print("\n📂 Categories:")
categories = db.query(Category).all()
for category in categories:
    book_count = len(category.books)
    print(f"   - {category.name} ({category.slug}) - {book_count} books")

db.close()