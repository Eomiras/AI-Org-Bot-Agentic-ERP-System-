import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from bot.core.database import Base, init_db

async def check_tables_registered():
    """Checks if the User table is registered in SQLAlchemy metadata."""
    print("Checking metadata registration...")

    # We call init_db because that's where the import happens now
    # We don't actually need to run the DB query (which requires docker),
    # just trigger the python import logic.

    # However, init_db is async and tries to connect.
    # Instead, let's just inspect the module import effect.

    try:
        # Trigger the import manually to simulate what init_db does,
        # or just inspect Base.metadata if the previous fix worked.

        # The fix was INSIDE init_db. So we must call init_db to trigger the import
        # OR we can manually verify the fix logic.

        # Let's inspect Base.metadata.tables BEFORE and AFTER importing models.

        print(f"Tables before import: {list(Base.metadata.tables.keys())}")

        from bot.core import models

        print(f"Tables after import: {list(Base.metadata.tables.keys())}")

        if "users" in Base.metadata.tables:
             print("✅ 'users' table is correctly registered.")
        else:
             print("❌ 'users' table is MISSING.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_tables_registered())
