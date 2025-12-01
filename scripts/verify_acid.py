import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

async def verify_acid_logic():
    print("--- 🏦 Verifying The Vault (ACID Logic) ---")

    # 1. Mock DB Session for Locking Check
    mock_session = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session
    mock_session_cm.__aexit__.return_value = None

    # Mock Select statement to check for with_for_update
    mock_stmt = MagicMock()
    mock_stmt.where.return_value = mock_stmt
    mock_stmt.with_for_update.return_value = mock_stmt

    # Patch internals
    # We must import first, then patch the module attributes
    import bot.core.ai.tools.economy
    bot.core.ai.tools.economy.AsyncSessionLocal = MagicMock(return_value=mock_session_cm)

    # Patch the 'select' function that was imported into the module namespace
    bot.core.ai.tools.economy.select = MagicMock(return_value=mock_stmt)

    # 2. Test get_or_create_account with lock=True
    print("Testing Row Locking...")
    from bot.core.ai.tools.economy import get_or_create_account

    await get_or_create_account(mock_session, 123, lock=True)

    if mock_stmt.with_for_update.called:
        print("✅ SELECT ... FOR UPDATE called.")
    else:
        print("❌ Locking NOT detected.")
        return False

    # 3. Test Transfer Logic (Negative Amount)
    print("Testing Sanity Checks...")
    from bot.core.ai.tools.economy import transfer_money

    # Tools must be invoked with a dict
    result = await transfer_money.ainvoke({"sender_id": 1, "receiver_id": 2, "amount": -100})

    if "Rejected" in result:
        print(f"✅ Negative Amount Rejected: {result}")
    else:
        print(f"❌ Negative Amount Allowed: {result}")
        return False

    print("\n--- 🚀 Vault Logic Verified! ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_acid_logic())
