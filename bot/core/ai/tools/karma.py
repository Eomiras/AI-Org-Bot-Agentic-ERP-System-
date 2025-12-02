from langchain_core.tools import tool
from bot.core.database import async_session_maker
from bot.core.models import KarmaCore, KarmaLog
from sqlalchemy import select, desc

@tool
async def get_user_karma_status(user_id: int):
    """
    Retrieves the current Karma Core status for a user.
    Returns Dictionary with total_karma, tier, last_activity, etc.
    Use this tool to answer questions about a user's reputation or tier.
    """
    async with async_session_maker() as session:
        result = await session.execute(select(KarmaCore).where(KarmaCore.user_id == user_id))
        karma = result.scalar_one_or_none()

        if not karma:
            return {"status": "User not found in Karma Core", "tier": "Novize", "total_karma": 0}

        return {
            "user_id": karma.user_id,
            "total_karma": karma.total_karma,
            "tier": karma.karma_tier,
            "is_afk": karma.is_afk,
            "last_activity": str(karma.last_activity) if karma.last_activity else None,
            "decay_override": str(karma.decay_override_until) if karma.decay_override_until else None
        }

@tool
async def get_karma_audit_log(user_id: int, limit: int = 5):
    """
    Retrieves the last N entries from the Karma Log for a user.
    Use this to explain WHY a user has a certain score (History).
    """
    async with async_session_maker() as session:
        stmt = select(KarmaLog).where(KarmaLog.user_id == user_id).order_by(desc(KarmaLog.timestamp)).limit(limit)
        result = await session.execute(stmt)
        logs = result.scalars().all()

        output = []
        for log in logs:
            output.append({
                "timestamp": str(log.timestamp),
                "change": log.points_change,
                "reason": log.reason,
                "source": log.source_id
            })
        return output
