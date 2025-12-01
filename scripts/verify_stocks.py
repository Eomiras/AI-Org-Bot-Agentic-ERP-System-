import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

from bot.cogs.economy.stocks import StockMarketCog

async def verify_stocks():
    print("--- 📈 Verifying Stock Market Logic ---")

    # 1. Mock DB Session
    mock_session = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session
    mock_session_cm.__aexit__.return_value = None

    # Mock session.begin() to return an async CM
    mock_transaction_cm = AsyncMock()
    mock_transaction_cm.__aenter__.return_value = None
    mock_transaction_cm.__aexit__.return_value = None
    mock_session.begin = MagicMock(return_value=mock_transaction_cm)

    import bot.cogs.economy.stocks
    bot.cogs.economy.stocks.AsyncSessionLocal = MagicMock(return_value=mock_session_cm)

    # 2. Simulate Register Company
    print("Testing Company Registration...")

    # Mock flush to set ID
    def mock_flush_side_effect():
        # Iterate over objects added to session and set IDs
        for call in mock_session.add.call_args_list:
            obj = call[0][0]
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = 999 # Assign Mock ID

    mock_session.flush.side_effect = mock_flush_side_effect

    # Mock checks
    mock_session.execute.return_value.scalar_one_or_none.return_value = None # No existing name

    # Mock User Account
    user_acc = MagicMock(balance=100000)

    # We need to simulate the sequence of execute calls again?
    # 1. Check Name
    # 2. Lock User

    mock_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: None), # Name check
        MagicMock(scalar_one_or_none=lambda: user_acc) # User lock
    ]

    mock_bot = MagicMock()
    cog = StockMarketCog(mock_bot)
    ctx = AsyncMock()
    ctx.author.id = 123

    await cog.register.callback(cog, ctx, "SpaceX")

    # Verify Fee Deduction
    if user_acc.balance == 50000:
        print("✅ Registration Fee Deducted.")
    else:
        print(f"❌ Fee Logic Fail: {user_acc.balance}")
        return False

    # Verify Company Creation
    # session.add called for: Company, User(Corp), BankAccount(Corp), Shareholder(CEO), Transaction
    if mock_session.add.call_count >= 5:
        print("✅ Company Records Created.")
    else:
        print("❌ Missing DB Records.")
        return False

    print("\n--- 🚀 Stock System Verified! ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_stocks())
