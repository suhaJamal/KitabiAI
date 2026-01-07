import sys
from pathlib import Path

# Add parent directory to path so we can import app module
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()

print("✅ Tables in database:")
for table in tables:
    print(f"\n📋 Table: {table}")
    columns = inspector.get_columns(table)
    for col in columns:
        col_type = str(col['type'])
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"   - {col['name']}: {col_type} ({nullable})")