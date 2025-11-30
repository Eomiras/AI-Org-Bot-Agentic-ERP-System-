import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from bot.core.database import Base
from bot.core import models # Force import

async def check_economy_tables():
    """Checks if the Economy tables are registered in SQLAlchemy metadata."""
    print("Checking metadata registration for Economy...")

    tables = Base.metadata.tables.keys()
    print(f"Registered tables: {list(tables)}")

    expected = ["users", "bank_accounts", "transactions"]

    missing = [t for t in expected if t not in tables]

    if not missing:
         print("✅ All Economy tables are correctly registered.")
    else:
         print(f"❌ Missing tables: {missing}")

if __name__ == "__main__":
    asyncio.run(check_economy_tables())
