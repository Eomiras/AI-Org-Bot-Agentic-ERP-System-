import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from bot.core.database import Base
from bot.core import models # Force import to register tables

# Mocking Arq/Redis for verification (so we don't crash on imports)
# Real runtime requires Redis, but we just want to check Python syntax/structure.

async def verify_full_system():
    print("--- 🔍 Verifying Full System Integration ---")

    # 1. Check Database Models
    print("\n[Database] Checking Table Registration...")
    tables = list(Base.metadata.tables.keys())
    expected_tables = ["users", "bank_accounts", "transactions"]

    missing = [t for t in expected_tables if t not in tables]
    if missing:
        print(f"❌ Missing Tables: {missing}")
        return False
    else:
        print(f"✅ Tables Verified: {tables}")

    # 2. Check Module Imports (Simulating what main.py does)
    print("\n[Modules] Checking Cog Imports...")
    extensions = [
        "bot.cogs.authentication",
        "bot.cogs.economy.cog",
        "bot.cogs.media.cog",
        "bot.cogs.compliance.cog",
    ]

    for ext in extensions:
        try:
            __import__(ext, fromlist=[''])
            print(f"✅ Imported: {ext}")
        except ImportError as e:
            print(f"❌ Failed to import {ext}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error importing {ext}: {e}")
            return False

    # 3. Check Worker Configuration
    print("\n[Worker] Checking Worker Settings...")
    try:
        from bot.worker import WorkerSettings
        if hasattr(WorkerSettings, 'functions') and len(WorkerSettings.functions) >= 2:
             print(f"✅ Worker Functions: {[f.__name__ for f in WorkerSettings.functions]}")
        else:
             print("❌ WorkerSettings missing functions.")
             return False
    except ImportError as e:
        print(f"❌ Failed to import WorkerSettings: {e}")
        return False

    print("\n--- 🚀 System Ready! ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_full_system())
