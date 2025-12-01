import asyncio
import os
import sys
from unittest.mock import MagicMock

sys.path.append(os.getcwd())

from bot.core.models import User

def verify_risk_math():
    print("--- 🛡️ Verifying Risk Score Math ---")

    # Case 1: Standard (50/50/50)
    # ER = 0.5*50 + 0.4*50 + 0.1*50 = 25 + 20 + 5 = 50.
    # Risk = 100 - 50 = 50.
    u1 = User(trust_score=50, duty_score=50, skill_score=50)
    print(f"Case 1 (50/50/50): ER={u1.effective_reputation}, Risk={u1.risk_score}")
    if u1.risk_score == 50.0:
        print("✅ Standard Case Verified.")
    else:
        print(f"❌ Math Error Case 1: {u1.risk_score}")
        return False

    # Case 2: High Performer (90/90/90)
    # ER = 0.5*90 + 0.4*90 + 0.1*90 = 45 + 36 + 9 = 90.
    # Risk = 10.
    u2 = User(trust_score=90, duty_score=90, skill_score=90)
    print(f"Case 2 (90/90/90): Risk={u2.risk_score}")
    if u2.risk_score == 10.0:
        print("✅ High Performer Verified.")
    else:
        print("❌ Math Error Case 2")
        return False

    # Case 3: Low Duty (10), High Trust (90)
    # ER = 0.5*10 + 0.4*90 + 0.1*50 = 5 + 36 + 5 = 46.
    # Risk = 54.
    u3 = User(duty_score=10, trust_score=90, skill_score=50)
    print(f"Case 3 (Low Duty): Risk={u3.risk_score}")
    if u3.risk_score == 54.0:
        print("✅ Low Duty Weighting Verified.")
    else:
        print("❌ Math Error Case 3")
        return False

    print("\n--- 🚀 Risk Logic Verified! ---")
    return True

if __name__ == "__main__":
    verify_risk_math()
