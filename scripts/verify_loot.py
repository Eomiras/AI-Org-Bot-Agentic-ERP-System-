import asyncio
import os
import sys

sys.path.append(os.getcwd())

from bot.cogs.economy.loot import LootCalculator

def verify_loot_math():
    print("--- 💰 Verifying Loot Split Math (Integer Policy) ---")

    # Case 1: Standard
    gross = 1_250_450
    tax = 0.10
    players = 4

    calc = LootCalculator(gross, tax, players)
    res = calc.calculate()

    print(f"Input: {gross}")
    print(f"Org Share (Tax + Dust): {res['org_share']}")
    print(f"Payout per Player: {res['payout']}")

    total_distributed = res['org_share'] + (res['payout'] * players)

    if total_distributed == gross:
        print("✅ ACID Check Passed: Sum equals Gross.")
    else:
        print(f"❌ ACID Fail: {total_distributed} != {gross}")
        return False

    # Case 2: Ugly Numbers (High Dust)
    gross = 100
    tax = 0.10 # 10 tax
    players = 3 # Net 90 / 3 = 30. Remainder 0.

    # Wait, 100 * 0.1 = 10. Net 90. 90/3 = 30. Perfect.

    # Try: 101
    # Tax: 10. Net 91.
    # Payout: 91 // 3 = 30.
    # Payout Total: 90.
    # Remainder: 1.
    # Org Share: 10 + 1 = 11.
    # Sum: 11 + 90 = 101. Correct.

    calc2 = LootCalculator(101, 0.10, 3)
    res2 = calc2.calculate()
    if res2['org_share'] == 11 and res2['payout'] == 30:
        print("✅ Dust Calculation Verified.")
    else:
        print(f"❌ Dust Logic Fail: {res2}")
        return False

    print("\n--- 🚀 Loot Logic Verified! ---")
    return True

if __name__ == "__main__":
    verify_loot_math()
