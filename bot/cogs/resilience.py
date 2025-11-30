import discord
from discord.ext import commands
from discord import option
from sqlalchemy import select, update
from bot.core.database import AsyncSessionLocal
from bot.core.models import User
from datetime import datetime, timedelta, timezone

class ResilienceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="afk", description="Set your status to AfK (Away from Keyboard) to freeze reputation decay.")
    @option("reason", description="Reason for absence", required=False)
    @option("days", description="Expected days of absence", default=7)
    async def afk(self, ctx: discord.ApplicationContext, reason: str = "Leave of Absence", days: int = 7):
        await ctx.defer(ephemeral=True)

        until = datetime.now(timezone.utc) + timedelta(days=days)

        async with AsyncSessionLocal() as session:
            # Update User
            stmt = update(User).where(User.discord_id == ctx.author.id).values(
                is_afk=True,
                afk_reason=reason,
                afk_until=until
            )
            result = await session.execute(stmt)
            await session.commit()

            if result.rowcount == 0:
                # User might not exist yet if they never verified/banked
                # Ideally create user here, but for simplicity just warn
                await ctx.respond("❌ User record not found. Please run `/balance` or `/verify` first to initialize your account.", ephemeral=True)
                return

        await ctx.respond(f"✅ **AfK Status Set.**\nReason: {reason}\nUntil: {until.strftime('%Y-%m-%d')}\n*Your reputation decay is now frozen.*", ephemeral=True)

    @discord.slash_command(name="back", description="Remove AfK status.")
    async def back(self, ctx: discord.ApplicationContext):
        async with AsyncSessionLocal() as session:
            stmt = update(User).where(User.discord_id == ctx.author.id).values(
                is_afk=False,
                afk_reason=None,
                afk_until=None
            )
            await session.execute(stmt)
            await session.commit()

        await ctx.respond("👋 Welcome back, Commander! AfK status removed.", ephemeral=True)

def setup(bot):
    bot.add_cog(ResilienceCog(bot))
