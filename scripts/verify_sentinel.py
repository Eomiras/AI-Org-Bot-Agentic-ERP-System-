import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

async def verify_sentinel_tools():
    print("--- 🛡️ Verifying Sentinel Tools ---")

    # 1. Mock DB Session
    mock_session = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session
    mock_session_cm.__aexit__.return_value = None

    # Mock Redis
    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock()
    mock_redis.aclose = AsyncMock()
    sys.modules['redis.asyncio'] = MagicMock()
    sys.modules['redis.asyncio'].Redis.from_url.return_value = mock_redis

    # Patch internals
    import bot.core.ai.tools.sentinel
    bot.core.ai.tools.sentinel.AsyncSessionLocal = MagicMock(return_value=mock_session_cm)

    # 2. Test Get Risk Profile
    from bot.core.ai.tools.sentinel import get_user_risk_profile

    # Mock User
    mock_user = MagicMock()
    mock_user.risk_score = 75.5
    mock_user.duty_score = 20
    mock_user.trust_score = 10
    mock_user.skill_score = 50

    # execute returns a Result object (synchronous mostly)
    # We ensure scalar_one_or_none is a standard Mock returning our user
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    print("Executing get_user_risk_profile...")
    # Invoke Tool (using .invoke or .ainvoke if it's a Tool)
    # The function is decorated with @tool, so it's a StructuredTool.
    # It seems 'ainvoke' expects a dict input.

    res = await get_user_risk_profile.ainvoke({"user_id": 123})
    print(f"Result: {res}")

    if "Risk Score: 75.50" in res:
        print("✅ Risk Profile Fetched.")
    else:
        print("❌ Profile Fetch Failed.")
        return False

    # 3. Test Lockout
    from bot.core.ai.tools.sentinel import trigger_lockout
    print("Executing trigger_lockout...")

    res_lock = await trigger_lockout.ainvoke({"user_id": 123, "reason": "Test"})
    print(f"Result: {res_lock}")

    if "PROTOCOL ACTIVE" in res_lock:
        print("✅ Lockout Protocol Activated.")
    else:
        print("❌ Lockout Failed.")
        return False

    print("\n--- 🚀 Sentinel System Verified! ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_sentinel_tools())
