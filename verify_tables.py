from app.models.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()

print("✅ Tables in database:")
for table in tables:
    print(f"  - {table}")