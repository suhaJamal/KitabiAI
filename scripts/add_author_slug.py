# add_author_slug.py
from app.models.database import engine
from sqlalchemy import text

sql = text("""
ALTER TABLE books 
ADD COLUMN IF NOT EXISTS author_slug VARCHAR(200);
""")

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()
    print("✅ author_slug column added!")