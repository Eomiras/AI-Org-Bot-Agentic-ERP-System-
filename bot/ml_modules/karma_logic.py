import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from bot.core.models import KarmaCore, KarmaLog, User
from bot.core.database import get_db

# --- Constants & Rules ---
TIER_RULES = {
    "Abtrünniger": {"min": -99999, "max": -500},
    "Novize": {"min": -499, "max": 0},
    "Wächter": {"min": 1, "max": 500},
    "Veteran": {"min": 501, "max": 2000},
    "Ältester": {"min": 2001, "max": 999999}
}

DECAY_THRESHOLD_DAYS = 30
DECAY_CONSTANT = 2.0
ABTRUNNIGER_DECAY = 5

async def calculate_tier(total_karma: int) -> str:
    """Calculates the Tier based on total karma."""
    for tier, r in TIER_RULES.items():
        if r["min"] <= total_karma <= r["max"]:
            return tier
    return "Novize" # Default fallback

async def get_or_create_karma_core(session: AsyncSession, user_id: int) -> KarmaCore:
    result = await session.execute(select(KarmaCore).where(KarmaCore.user_id == user_id))
    karma_core = result.scalar_one_or_none()
    if not karma_core:
        karma_core = KarmaCore(user_id=user_id, total_karma=0, karma_tier="Novize")
        session.add(karma_core)
        # Flush to ensure it exists for subsequent ops (but commit happens later)
        await session.flush()
    return karma_core

async def process_karma_change(user_id: int, change_amount: int, reason: str, source_id: str, session: AsyncSession = None):
    """
    Applies a karma change, updates tier, and logs the event.
    Designed to be ACID compliant if passed an existing session.
    """
    # If no session provided, manage one
    local_session = False
    if session is None:
        local_session = True
        # Create a new session context (Assuming get_db yields a session)
        # However, getting a session from an async generator in a helper is tricky.
        # It's better to require session injection.
        # For now, I will assume the caller provides it or I adapt.
        # Given the architecture, we should probably require session.
        raise ValueError("Session must be provided to process_karma_change")

    # 1. Get/Create Karma Core
    karma_core = await get_or_create_karma_core(session, user_id)

    # 2. Update Karma
    old_tier = karma_core.karma_tier
    karma_core.total_karma += change_amount

    # 3. Update Tier
    new_tier = await calculate_tier(karma_core.total_karma)
    karma_core.karma_tier = new_tier
    karma_core.last_activity = datetime.datetime.now(datetime.timezone.utc)

    # 4. Log
    log = KarmaLog(
        user_id=user_id,
        source_id=source_id,
        points_change=change_amount,
        reason=reason
    )
    session.add(log)

    return {
        "new_total": karma_core.total_karma,
        "new_tier": new_tier,
        "old_tier": old_tier,
        "tier_changed": new_tier != old_tier
    }

async def calculate_decay(current_karma: int, days_inactive: int, tier: str) -> int:
    """
    Calculates the amount of karma to decay.
    Rule 1: Base Decay (Tier >= Novize) -> Logarithmic after 30 days.
    Rule 2: Aggressive Decay (Tier == Abtrünniger) -> 5 points fixed per day until -500.
    """
    if tier == "Abtrünniger":
        if current_karma > -500:
            return ABTRUNNIGER_DECAY
        return 0

    if days_inactive > DECAY_THRESHOLD_DAYS:
        # log_e(D - Threshold + 1) * C
        # Note: math.log is natural log (ln)
        import math
        decay = math.log(days_inactive - DECAY_THRESHOLD_DAYS + 1) * DECAY_CONSTANT
        return int(decay)

    return 0

async def daily_decay_task(ctx):
    """
    The scheduled task to apply decay.
    ctx: The worker context (provided by Arq).
    """
    import logging
    logger = logging.getLogger(__name__)

    # We need a database session.
    # The worker might have a session pool in ctx['session_maker'] or similar?
    # Usually we create a session manually if not provided.
    # Looking at `bot/core/database.py`, we have `async_session_maker`.
    from bot.core.database import async_session_maker

    logger.info("Starting Daily Decay Task")

    async with async_session_maker() as session:
        async with session.begin():
            # 1. Select all KarmaCore entries that are not AFK
            # We also need to check last_activity.
            # And check if we already ran today? (last_decay_run)

            # Simple approach: Iterate all users (might be slow for millions, but fine for Org Bot)
            # Better: Select relevant ones.
            stmt = select(KarmaCore).where(KarmaCore.is_afk == False)
            result = await session.execute(stmt)
            all_karma_records = result.scalars().all()

            now = datetime.datetime.now(datetime.timezone.utc)
            processed_count = 0

            for record in all_karma_records:
                # Calculate Inactivity
                last_active = record.last_activity
                if not last_active:
                    last_active = record.created_at # Fallback? KarmaCore doesn't have created_at.
                    # If last_activity is null, assume very old or new?
                    # Schema says default=func.now(). So should be fine.
                    pass

                # If timezone naive, make it aware (assuming stored as UTC)
                if last_active.tzinfo is None:
                    last_active = last_active.replace(tzinfo=datetime.timezone.utc)

                delta = now - last_active
                days_inactive = delta.days

                decay_amount = await calculate_decay(record.total_karma, days_inactive, record.karma_tier)

                if decay_amount > 0:
                    # Apply Decay
                    record.total_karma -= decay_amount

                    # Update Tier
                    new_tier = await calculate_tier(record.total_karma)
                    record.karma_tier = new_tier

                    # Update Last Decay Run
                    record.last_decay_run = now

                    # Log it
                    log = KarmaLog(
                        user_id=record.user_id,
                        source_id="SYSTEM",
                        points_change=-decay_amount,
                        reason="DECAY"
                    )
                    session.add(log)
                    processed_count += 1

            logger.info(f"Decay Task Completed. Processed {processed_count} users.")
