import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

async def verify_loot_fix():
    print("--- 🛠️ Verifying Loot Integrity Fix ---")

    # 1. Mock DB Session
    mock_session = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session
    mock_session_cm.__aexit__.return_value = None

    # Patch AsyncSessionLocal in the module
    import bot.cogs.economy.loot
    bot.cogs.economy.loot.AsyncSessionLocal = MagicMock(return_value=mock_session_cm)

    # 2. Simulate "Confirm" with missing account
    # We mock the select result to return None (no account)
    # Then we check if session.add(account) was called.

    mock_result_treasury = MagicMock()
    mock_result_treasury.scalar_one_or_none.return_value = MagicMock() # Treasury exists

    mock_result_user = MagicMock()
    mock_result_user.scalar_one_or_none.return_value = None # User MISSING

    # execute is called multiple times.
    # 1. Treasury Lock
    # 2. User Lock (for loop)
    # 3. User check (inside if not account)

    mock_session.execute.side_effect = [
        mock_result_treasury, # Treasury
        mock_result_user,     # User Account Lock (None)
        mock_result_user,     # User Exists Check (None)
    ]

    # Mock Interaction & View
    mock_bot = MagicMock()
    view = bot.cogs.economy.loot.ConfirmSplitView(
        mock_bot,
        {"gross": 100, "org_share": 10, "payout": 90, "remainder": 0},
        [MagicMock(id=123)], # 1 Participant
        999
    )

    mock_interaction = AsyncMock()
    mock_interaction.user.id = 999

    print("Executing Confirm (Simulating Missing Account)...")
    await view.confirm(None, mock_interaction)

    # 3. Verification
    # Check if session.add was called at least 3 times:
    # 1. New User
    # 2. New BankAccount
    # 3. Transaction Log (Player)
    # 4. Transaction Log (Org)

    add_calls = mock_session.add.call_count
    print(f"Session.add called {add_calls} times.")

    if add_calls >= 4:
        print("✅ Account Creation & Logging detected.")
    else:
        print("❌ Missing DB operations (Fix failed).")
        return False

    print("\n--- 🚀 Fix Verified! ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_loot_fix())
