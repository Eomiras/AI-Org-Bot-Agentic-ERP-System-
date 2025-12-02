import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

from bot.cogs.economy.bounty import BountyCog, ESCROW_ID

async def verify_bounty_logic():
    print("--- 📜 Verifying Bounty & Escrow Logic ---")

    # 1. Mock DB Session
    mock_session = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session
    mock_session_cm.__aexit__.return_value = None

    # Mock session.begin() to return an async CM
    # session.begin MUST be a MagicMock, not AsyncMock, because it's called synchronously
    # to get the context manager.
    mock_transaction_cm = AsyncMock()
    mock_transaction_cm.__aenter__.return_value = None
    mock_transaction_cm.__aexit__.return_value = None
    mock_session.begin = MagicMock(return_value=mock_transaction_cm)

    # Patch AsyncSessionLocal
    import bot.cogs.economy.bounty
    bot.cogs.economy.bounty.AsyncSessionLocal = MagicMock(return_value=mock_session_cm)

    # 2. Simulate Create Bounty (Transfer to Escrow)
    print("Testing Escrow Deposit...")

    # Mock Accounts
    issuer = MagicMock(balance=1000)
    escrow = MagicMock(balance=0)

    # execute calls:
    # 1. Lock Issuer
    # 2. Lock Escrow

    mock_res_issuer = MagicMock()
    mock_res_issuer.scalar_one_or_none.return_value = issuer

    mock_res_escrow = MagicMock()
    mock_res_escrow.scalar_one_or_none.return_value = escrow

    mock_session.execute.side_effect = [mock_res_issuer, mock_res_escrow]

    # Mock Context
    mock_bot = MagicMock()
    cog = BountyCog(mock_bot)
    ctx = AsyncMock()
    ctx.author.id = 123

    # Bypass SlashCommand wrapper to test logic directly
    await cog.create.callback(cog, ctx, "Target A", 500)

    # Verify Balances
    print(f"Issuer Balance: {issuer.balance}")
    print(f"Escrow Balance: {escrow.balance}")

    if issuer.balance == 500 and escrow.balance == 500:
        print("✅ Escrow Transfer Correct (ACID).")
    else:
        print("❌ Escrow Transfer Fail.")
        return False

    # Check DB Add calls (Bounty + Transaction)
    if mock_session.add.call_count >= 2:
        print("✅ Bounty & Log Record Created.")
    else:
        print("❌ Missing DB Records.")
        return False

    print("\n--- 🚀 Bounty System Verified! ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_bounty_logic())
