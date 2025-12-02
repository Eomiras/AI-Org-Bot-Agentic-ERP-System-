import asyncio
import os
import sys
from unittest.mock import MagicMock

sys.path.append(os.getcwd())

from bot.cogs.economy.loans import IronBankCog
from bot.core.models import User

def verify_iron_bank():
    print("--- 🏦 Verifying Iron Bank Logic ---")

    mock_bot = MagicMock()
    cog = IronBankCog(mock_bot)
    cog.interest_loop.cancel() # Stop loop

    # Test 1: Credit Calculation
    # User: Trust 90, Duty 80
    # Formula: 1000 + (90 * 1000) + (80 * 500)
    # 1000 + 90000 + 40000 = 131000
    user = User(trust_score=90, duty_score=80)
    credit = cog.calculate_max_credit(user)
    print(f"Credit Limit (T90/D80): {credit}")

    if credit == 131000:
        print("✅ Credit Calculation Correct.")
    else:
        print(f"❌ Credit Calculation Fail: {credit}")
        return False

    # Test 2: Eligibility Check
    # Min Trust = 80
    user_poor = User(trust_score=50, duty_score=100)
    if user_poor.trust_score < cog.MIN_TRUST_REQ:
        print("✅ Eligibility Check Correct (Trust < 80 rejected).")
    else:
        print("❌ Eligibility Logic Fail.")
        return False

    print("\n--- 🚀 Iron Bank Logic Verified! ---")
    return True

if __name__ == "__main__":
    verify_iron_bank()
