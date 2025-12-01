import asyncio
import os
import sys
from unittest.mock import MagicMock

sys.path.append(os.getcwd())

from bot.cogs.economy.reputation import ReputationCog

def verify_decay_math():
    print("--- 📉 Verifying Reputation Decay Logic ---")

    # Mock Bot
    mock_bot = MagicMock()
    cog = ReputationCog(mock_bot)
    # Stop loop for test
    cog.decay_loop.cancel()

    # Test 1: Standard Decay
    # Score 100, Inactive 10 days
    # Formula: 100 * (1 - 0.005)^10
    # 0.995^10 approx 0.951
    # 100 * 0.951 = 95
    res1 = cog.calculate_new_score(100, 10)
    print(f"Test 1 (100 -> 10 days): {res1}")
    if 90 < res1 < 100:
        print("✅ Standard Decay within expected range.")
    else:
        print(f"❌ Math Error: {res1}")
        return False

    # Test 2: Floor Check
    # Score 21, Inactive 100 days
    # Should stay at 20 (MIN_SCORE)
    res2 = cog.calculate_new_score(21, 100)
    print(f"Test 2 (21 -> 100 days): {res2}")
    if res2 == 20:
        print("✅ Floor Guard working.")
    else:
        print(f"❌ Floor Error: {res2}")
        return False

    # Test 3: Zero days (Should be same)
    res3 = cog.calculate_new_score(80, 0)
    if res3 == 80:
        print("✅ Zero Days verified.")
    else:
        print("❌ Zero Days Error.")

    print("\n--- 🚀 Reputation Logic Verified! ---")
    return True

if __name__ == "__main__":
    verify_decay_math()
