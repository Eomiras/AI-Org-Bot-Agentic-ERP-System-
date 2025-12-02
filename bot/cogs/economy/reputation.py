import discord
from discord.ext import commands, tasks
from sqlalchemy import select, update
from datetime import datetime, timedelta, timezone
from math import floor
from bot.core.database import AsyncSessionLocal
from bot.core.models import User
from bot.core.logger import logger

class ReputationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DECAY_RATE = 0.005 # 0.5% per day
        self.MIN_SCORE = 20 # Floor
        self.INACTIVE_DAYS = 7
        self.decay_loop.start()

    def cog_unload(self):
        self.decay_loop.cancel()

    def calculate_new_score(self, current_score: int, days_inactive: int) -> int:
        """
        Karma Decay Formula:
        New = Max(Old * (1 - Rate)^Days, Min)
        """
        # Calculate effective decay factor
        # If user is inactive for 10 days, but threshold is 7, do we decay for 3 days or 10?
        # Design says: "Tage ohne Aktivität". Usually total days.

        factor = (1 - self.DECAY_RATE) ** days_inactive
        new_score = floor(current_score * factor)
        return max(new_score, self.MIN_SCORE)

    @tasks.loop(hours=24) # Runs daily
    async def decay_loop(self):
        logger.info("⏳ Starting Reputation Decay Cycle...")
        async with AsyncSessionLocal() as session:
            # 1. Fetch all users who are NOT AFK
            # We fetch user_id, scores, last_activity
            stmt = select(User).where(User.is_afk == False)
            result = await session.execute(stmt)
            users = result.scalars().all()

            now = datetime.now(timezone.utc)
            decay_count = 0

            for user in users:
                if not user.last_activity:
                    continue

                # Ensure timezone awareness
                last_active = user.last_activity
                if last_active.tzinfo is None:
                    last_active = last_active.replace(tzinfo=timezone.utc)

                delta = now - last_active
                if delta.days > self.INACTIVE_DAYS:
                    # Apply Decay
                    # Design Mandate: Decay affects primarily Duty Score.
                    # Trust is stickier (harder to gain, harder to lose via inactivity).

                    old_duty = user.duty_score or 50
                    new_duty = self.calculate_new_score(old_duty, delta.days)

                    # Trust decays much slower or not at all for pure inactivity (unless "Bad Debt")
                    # For now, we only decay Duty as per "The Sentinel" spec section 5.D

                    if new_duty != old_duty:
                        user.duty_score = new_duty
                        decay_count += 1

            if decay_count > 0:
                await session.commit()
                logger.info(f"✅ Reputation Decay applied to {decay_count} users.")
            else:
                logger.info("✅ No users required decay.")

    @decay_loop.before_loop
    async def before_decay_loop(self):
        await self.bot.wait_until_ready()

    @discord.slash_command(name="reputation", description="Check your Karma Core scores.")
    async def reputation(self, ctx: discord.ApplicationContext):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.discord_id == ctx.author.id))
            user = result.scalar_one_or_none()

            if not user:
                await ctx.respond("User not found.", ephemeral=True)
                return

            embed = discord.Embed(title="💠 Karma Core Matrix", color=discord.Color.purple())
            embed.add_field(name="Trust Score", value=f"{user.trust_score or 50} / 100", inline=True)
            embed.add_field(name="Duty Score", value=f"{user.duty_score or 50} / 100", inline=True)

            status = "🟢 Active"
            if user.is_afk:
                status = f"❄️ AfK (Frozen) until {user.afk_until.strftime('%Y-%m-%d') if user.afk_until else '?'}"

            embed.add_field(name="Status", value=status, inline=False)
            await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(ReputationCog(bot))
