"""
Verify Azure Setup - Phase 3
Checks: Database, Blob Storage, App Service
"""

import sys
from pathlib import Path
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("🔍 Azure Setup Verification - Phase 3")
print("=" * 60)

# ============================================================================
# 1. Check Environment Variables
# ============================================================================
print("\n📋 Step 1: Checking Environment Variables\n")

from dotenv import load_dotenv
load_dotenv()

required_vars = {
    "DATABASE_URL": "Azure PostgreSQL connection string",
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": "Document Intelligence endpoint",
    "AZURE_DOCUMENT_INTELLIGENCE_KEY": "Document Intelligence key",
    "AZURE_STORAGE_CONNECTION_STRING": "Azure Blob Storage connection string",
    "AZURE_STORAGE_CONTAINER_NAME": "Azure Blob Storage container name",
}

all_vars_present = True

for var_name, description in required_vars.items():
    value = os.getenv(var_name)
    if value:
        # Mask sensitive values
        if "KEY" in var_name or "PASSWORD" in var_name or "CONNECTION_STRING" in var_name:
            display_value = f"{value[:20]}...{value[-10:]}" if len(value) > 30 else "***"
        else:
            display_value = value
        print(f"   ✅ {var_name}")
        print(f"      {display_value}")
    else:
        print(f"   ❌ {var_name} - MISSING!")
        print(f"      Required for: {description}")
        all_vars_present = False

if not all_vars_present:
    print("\n⚠️  WARNING: Some environment variables are missing!")
    print("   Add them to your .env file")

# ============================================================================
# 2. Check Database Connection
# ============================================================================
print("\n📋 Step 2: Checking Database Connection\n")

try:
    from app.models.database import engine, SessionLocal, Book
    from sqlalchemy import inspect

    # Test connection
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"   ✅ Database connection successful!")
    print(f"   📊 Found {len(tables)} tables: {', '.join(tables)}")

    # Check if Book table has new columns
    if 'books' in tables:
        columns = [col['name'] for col in inspector.get_columns('books')]
        required_columns = [
            'html_url', 'markdown_url', 'pages_jsonl_url',
            'sections_jsonl_url', 'pdf_url', 'cover_image_url',
            'files_generated_at'
        ]

        missing_columns = [col for col in required_columns if col not in columns]

        if missing_columns:
            print(f"   ⚠️  Missing columns in 'books' table: {', '.join(missing_columns)}")
            print(f"   ➡️  Run: python reset_db.py")
        else:
            print(f"   ✅ All required columns present in 'books' table")

    # Check if we can query
    db = SessionLocal()
    try:
        book_count = db.query(Book).count()
        print(f"   📚 Books in database: {book_count}")
    finally:
        db.close()

except Exception as e:
    print(f"   ❌ Database connection failed!")
    print(f"      Error: {str(e)}")

# ============================================================================
# 3. Check Azure Blob Storage Connection
# ============================================================================
print("\n📋 Step 3: Checking Azure Blob Storage\n")

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "books")

if not connection_string:
    print("   ❌ AZURE_STORAGE_CONNECTION_STRING not set in .env")
    print("   ➡️  Get it from: Azure Portal → Storage Account → Access keys")
else:
    try:
        from azure.storage.blob import BlobServiceClient

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        # Check if container exists
        container_client = blob_service_client.get_container_client(container_name)

        if container_client.exists():
            print(f"   ✅ Azure Blob Storage connection successful!")
            print(f"   ✅ Container '{container_name}' exists")

            # List blobs (if any)
            blobs = list(container_client.list_blobs())
            if blobs:
                print(f"   📁 Files in container: {len(blobs)}")
                print(f"      Recent files:")
                for blob in blobs[:5]:  # Show first 5
                    size_kb = blob.size / 1024
                    print(f"      - {blob.name} ({size_kb:.1f} KB)")
            else:
                print(f"   📁 Container is empty (no files uploaded yet)")
        else:
            print(f"   ❌ Container '{container_name}' does not exist!")
            print(f"   ➡️  Create it in: Azure Portal → Storage Account → Containers")

    except ModuleNotFoundError:
        print("   ⚠️  azure-storage-blob package not installed")
        print("   ➡️  Run: pip install azure-storage-blob")
    except Exception as e:
        print(f"   ❌ Azure Blob Storage connection failed!")
        print(f"      Error: {str(e)}")

# ============================================================================
# 4. Check if azure_storage_service.py exists
# ============================================================================
print("\n📋 Step 4: Checking Azure Storage Service Implementation\n")

azure_service_path = Path(__file__).parent.parent / "app" / "services" / "azure_storage_service.py"

if azure_service_path.exists():
    print(f"   ✅ azure_storage_service.py exists")

    # Check if it's being used
    generation_path = Path(__file__).parent.parent / "app" / "routers" / "generation.py"
    with open(generation_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'azure_storage' in content:
            print(f"   ✅ generation.py is using azure_storage")
        else:
            print(f"   ⚠️  generation.py is still using local_storage")
            print(f"   ➡️  Update imports to use azure_storage_service")
else:
    print(f"   ❌ azure_storage_service.py does not exist!")
    print(f"   ➡️  Need to create: app/services/azure_storage_service.py")

# ============================================================================
# 5. Summary
# ============================================================================
print("\n" + "=" * 60)
print("📊 Verification Summary")
print("=" * 60)

print("\n✅ = Ready")
print("⚠️  = Needs attention")
print("❌ = Missing/Failed")

print("\nNext steps:")
print("1. If environment variables are missing → Add to .env")
print("2. If database columns are missing → Run: python reset_db.py")
print("3. If Azure Storage connection fails → Check connection string")
print("4. If azure_storage_service.py missing → Create implementation")
print("5. If using local_storage → Update imports to azure_storage")

print("\n" + "=" * 60)
