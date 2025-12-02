import asyncio
import os
import sys
from unittest.mock import MagicMock

sys.path.append(os.getcwd())

from bot.core.models import User
from bot.cogs.economy.loot import LootCalculator
from bot.cogs.economy.loans import IronBankCog

def verify_risk_economy():
    print("--- 💸 Verifying Risk-Based Economy ---")

    # 1. Test Tax Multiplier
    print("\n[Loot] Tax Calculation...")
    gross = 1000
    base_tax = 0.10

    # User A: Low Risk (0)
    # Tax should be 100
    calc_low = LootCalculator(gross, base_tax, 1, avg_risk_score=0.0)
    res_low = calc_low.calculate()
    print(f"Risk 0 -> Tax: {res_low['tax_base']}")

    # User B: High Risk (50)
    # Multiplier: 1 + (50 * 0.005) = 1.25
    # Effective Rate: 0.125
    # Tax should be 125
    calc_high = LootCalculator(gross, base_tax, 1, avg_risk_score=50.0)
    res_high = calc_high.calculate()
    print(f"Risk 50 -> Tax: {res_high['tax_base']}")

    if res_low['tax_base'] == 100 and res_high['tax_base'] == 125:
        print("✅ Tax Multiplier Correct.")
    else:
        print("❌ Tax Logic Fail.")
        return False

    # 2. Test Credit Multiplier
    print("\n[Iron Bank] Credit Limit...")
    mock_bot = MagicMock()
    bank = IronBankCog(mock_bot)
    bank.interest_loop.cancel()

    # User C: Trust 100, Duty 100, Skill 100 (Risk 0)
    # Base = 1000 + 100*1000 + 100*500 = 151,000
    u_safe = User(trust_score=100, duty_score=100, skill_score=100) # Risk 0
    limit_safe = bank.calculate_max_credit(u_safe)
    print(f"Risk 0 -> Limit: {limit_safe}")

    # User D: Trust 100, Duty 100, Skill 0 (Risk > 0?)
    # ER = 50 + 40 + 0 = 90. Risk = 10.
    # Base = 151,000
    # Multiplier = 1 - (10 * 0.01) = 0.9
    # Limit = 151,000 * 0.9 = 135,900
    u_risky = User(trust_score=100, duty_score=100, skill_score=0)
    print(f"DEBUG: ER={u_risky.effective_reputation}, Risk={u_risky.risk_score}")
    limit_risky = bank.calculate_max_credit(u_risky)
    print(f"Risk 10 -> Limit: {limit_risky}")

    if limit_risky == 135900:
        print("✅ Credit Multiplier Correct.")
    else:
        print(f"❌ Credit Logic Fail: {limit_risky}")
        return False

    print("\n--- 🚀 Risk Economy Verified! ---")
    return True

if __name__ == "__main__":
    verify_risk_economy()
