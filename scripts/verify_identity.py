import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

async def verify_identity():
    print("--- 🎨 Verifying ID Card Generator ---")

    # 1. Mock DB and Security
    # We are importing 'bot.ml_modules.identity'. It imports 'bot.core.database' and 'models'.
    # We must patch these before import or use a testing harness.

    # Since the module is not imported yet, let's patch sys.modules first for DB access.
    # However, 'identity.py' creates an async session context manager.

    # Let's import the function and patch the 'AsyncSessionLocal' inside the module if possible,
    # or just run it and see if it fails on DB connection (which we expect in sandbox).
    # But we want to test the IMAGE GENERATION logic mostly.

    try:
        from bot.ml_modules.identity import generate_id_card_task
        print("✅ Module imported.")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

    # 2. Mocking the DB Session Context
    # We will manually invoke the drawing logic if possible, or mock the whole DB block.
    # It's easier to mock the session.

    mock_session = AsyncMock()
    # Mock result of query
    mock_result = MagicMock()
    mock_user = MagicMock()
    mock_user.discord_id = 123456789
    mock_user.is_verified = True
    mock_user.pii_blob = "encrypted_blob"

    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    # Mock context manager
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session
    mock_session_cm.__aexit__.return_value = None

    # Patch AsyncSessionLocal in the module
    import bot.ml_modules.identity
    bot.ml_modules.identity.AsyncSessionLocal = MagicMock(return_value=mock_session_cm)

    # Patch decrypt_pii
    bot.ml_modules.identity.decrypt_pii = MagicMock(return_value="RobertsSpaceInd")

    # 3. Run Task
    print("Running Task (Mocked DB)...")
    try:
        result_path = await generate_id_card_task({}, 123456789)

        if os.path.exists(result_path):
            print(f"✅ Image Generated: {result_path}")
            # Check dimensions (Requires Pillow)
            from PIL import Image
            img = Image.open(result_path)
            print(f"✅ Dimensions: {img.size}")

            # Cleanup
            os.remove(result_path)
        else:
            print(f"❌ Image not found: {result_path}")
            return False

    except Exception as e:
        print(f"❌ Task Exception: {e}")
        return False

    # 4. Check Cog Import
    try:
        __import__("bot.cogs.identity", fromlist=[''])
        print("✅ Cog imported.")
    except Exception as e:
        print(f"❌ Cog import failed: {e}")
        return False

    print("\n--- 🚀 Identity System Verified! ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_identity())
