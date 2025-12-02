from langchain_core.tools import tool
from sqlalchemy import select, update
from datetime import datetime, timedelta, timezone
from bot.core.database import AsyncSessionLocal
from bot.core.models import User
import redis.asyncio as redis
from bot.core.config import settings

@tool
async def get_user_risk_profile(user_id: int) -> str:
    """
    Fetches the risk profile (Risk Score, Duty, Trust) of a user.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.discord_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return "User not found."

        return f"Risk Score: {user.risk_score:.2f} | Duty: {user.duty_score} | Trust: {user.trust_score} | Skill: {user.skill_score}"

@tool
async def trigger_lockout(user_id: int, reason: str = "Security Violation") -> str:
    """
    Locks a user out of the system for 12 hours.
    Used for repeated auth failures or fraud detection.
    """
    # 1. Redis Lock
    try:
        r = redis.Redis.from_url(settings.redis_url)
        key = f"security:lockout:{user_id}"
        await r.setex(key, 43200, "1") # 12 hours
        await r.aclose()
    except Exception as e:
        return f"Redis Error: {e}"

    # 2. DB Update (Log)
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        until = now + timedelta(hours=12)
        stmt = update(User).where(User.discord_id == user_id).values(lockout_until=until)
        await session.execute(stmt)
        await session.commit()

    return f"PROTOCOL ACTIVE: User {user_id} locked out until {until}. Reason: {reason}"
