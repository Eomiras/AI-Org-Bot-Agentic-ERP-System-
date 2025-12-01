import asyncio
import os
import sys

sys.path.append(os.getcwd())

def verify_resilience():
    print("--- 🛡️ Verifying Resilience & Security ---")

    # 1. Check Scripts
    scripts = ["scripts/backup_db.sh", "scripts/watchdog.py"]
    for s in scripts:
        if os.path.exists(s):
            print(f"✅ Script found: {s}")
        else:
            print(f"❌ Script missing: {s}")
            return False

    # 2. Check Cog Import
    try:
        __import__("bot.cogs.resilience", fromlist=[''])
        print("✅ Imported bot.cogs.resilience")
    except ImportError as e:
        print(f"❌ Failed to import Resilience Cog: {e}")
        return False

    # 3. Check DB Model Update
    # We check if User model has 'is_afk' attribute
    from bot.core.models import User
    if hasattr(User, 'is_afk'):
        print("✅ User model updated with 'is_afk'")
    else:
        print("❌ User model missing 'is_afk'")
        return False

    print("\n--- 🚀 Resilience System Verified! ---")
    return True

if __name__ == "__main__":
    verify_resilience()
