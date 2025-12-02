import discord
from discord.ext import commands
from discord import slash_command, Option
from bot.core.database import async_session_maker
from bot.ml_modules.karma_logic import process_karma_change, get_or_create_karma_core, TIER_RULES
from bot.core.models import KarmaCore, User
from sqlalchemy import select
from bot.core.logger import logger

class KarmaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TIER_ICONS = {
            "Abtrünniger": "💀",
            "Novize": "🌱",
            "Wächter": "🛡️",
            "Veteran": "⭐",
            "Ältester": "👑"
        }

    # --- Reaction Listeners (Upvote/Downvote) ---
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Ignore bot's own reactions
        if payload.user_id == self.bot.user.id:
            return

        # Define Emoji Mapping
        UPVOTE_EMOJI = "👍"
        DOWNVOTE_EMOJI = "👎"

        emoji = str(payload.emoji)
        if emoji not in [UPVOTE_EMOJI, DOWNVOTE_EMOJI]:
            return

        # Get DB Session
        async with async_session_maker() as session:
            async with session.begin():
                # 1. Identify Actor (Voter) and Target (Author)
                voter_id = payload.user_id

                # Fetch message to get author
                channel = self.bot.get_channel(payload.channel_id)
                if not channel:
                    return # Can't find channel

                try:
                    message = await channel.fetch_message(payload.message_id)
                except discord.NotFound:
                    return # Message deleted?

                target_id = message.author.id

                # Prevent self-voting
                if voter_id == target_id:
                    return

                # Ignore Bot targets
                if message.author.bot:
                    return

                # 2. Check Permissions & Weighting (Voter's Tier)
                voter_karma = await get_or_create_karma_core(session, voter_id)
                target_karma = await get_or_create_karma_core(session, target_id)

                voter_tier = voter_karma.karma_tier

                # Rule: Only Wächter (Tier III) and above can downvote
                if emoji == DOWNVOTE_EMOJI:
                    # Tiers: Abtrünniger, Novize, Wächter, Veteran, Ältester
                    # If logic helper has numerical or ordered tiers, use that.
                    # For now, explicit check.
                    if voter_tier in ["Abtrünniger", "Novize"]:
                        # Remove reaction and warn? Or just ignore?
                        # Design says: "Nur Nutzer ab Stufe III können Downvotes vergeben."
                        # Removing reaction is good feedback.
                        try:
                            await message.remove_reaction(emoji, payload.member)
                        except:
                            pass
                        return

                # Calculate Weight
                # Novize: x1, Wächter: x1.5, Veteran: x2, Ältester: x3
                # We cast to int.
                weights = {
                    "Abtrünniger": 0.5, # Reduced influence? Or standard? Design doesn't specify Abtrünniger weight, assume low.
                    "Novize": 1.0,
                    "Wächter": 1.5,
                    "Veteran": 2.0,
                    "Ältester": 3.0
                }
                weight = weights.get(voter_tier, 1.0)

                # Base Values
                # Upvote: +5 to +20 (Variable? Design says "Vergeben durch Upvotes... Novize +1").
                # Wait, "Karma-Erwerb" table says: "Nützlicher Beitrag: +5 bis +20".
                # But "Systemmechanik & Regeln" says: "Novize (Upvote = +1 Karma)".
                # Contradiction? I will use the Systemmechanik values as they are more specific about calculation.
                # Base Upvote = 1, Base Downvote = -1.

                base_points = 1 if emoji == UPVOTE_EMOJI else -1
                final_points = int(base_points * weight)

                # Apply
                reason = "UPVOTE" if emoji == UPVOTE_EMOJI else "DOWNVOTE"
                result = await process_karma_change(
                    user_id=target_id,
                    change_amount=final_points,
                    reason=reason,
                    source_id=str(voter_id),
                    session=session
                )

                # 3. Notifications (Tier Change)
                if result["tier_changed"]:
                    # Send DM or Channel msg
                    try:
                        user = await self.bot.fetch_user(target_id)
                        await user.send(
                            f"**Vault Archivist Status Update:**\n"
                            f"Your Karma Tier has changed from **{result['old_tier']}** to **{result['new_tier']}**.\n"
                            f"Current Karma: {result['new_total']}"
                        )
                    except:
                        pass # DMs closed

    # --- Slash Commands ---
    karma = slash_command(name="karma", description="Access the Karma Core system")

    @karma.command(name="status", description="View your current Reputation Status")
    async def status(self, ctx: discord.ApplicationContext, user: Option(discord.Member, "Target User", required=False)):
        target = user or ctx.author

        async with async_session_maker() as session:
            karma = await get_or_create_karma_core(session, target.id)

            embed = discord.Embed(
                title=f"Karma Core Protocol: {target.display_name}",
                color=discord.Color.gold() if karma.karma_tier == "Ältester" else discord.Color.blue()
            )

            icon = self.TIER_ICONS.get(karma.karma_tier, "❓")

            embed.add_field(name="Tier Class", value=f"{icon} **{karma.karma_tier}**", inline=True)
            embed.add_field(name="Total Karma", value=f"`{karma.total_karma}`", inline=True)

            # Progress Bar?
            # Find next tier
            next_tier_min = 999999
            next_tier_name = "Max"

            # Simple manual check
            if karma.total_karma < 0:
                 # Negative Karma logic
                 pass
            else:
                 # Positive
                 pass

            embed.add_field(name="Status", value="✅ Active" if not karma.is_afk else "💤 AFK/Frozen", inline=False)
            embed.set_footer(text=f"User ID: {target.id} • Vault Archivist Verified")

            await ctx.respond(embed=embed)

    @karma.command(name="log", description="View your Karma Audit Log")
    async def log(self, ctx: discord.ApplicationContext):
        async with async_session_maker() as session:
            # Need to fetch KarmaLog
            from bot.core.models import KarmaLog
            from sqlalchemy import desc

            stmt = select(KarmaLog).where(KarmaLog.user_id == ctx.author.id).order_by(desc(KarmaLog.timestamp)).limit(10)
            result = await session.execute(stmt)
            logs = result.scalars().all()

            if not logs:
                await ctx.respond("No records found in the Karma Archive.", ephemeral=True)
                return

            text = "**Recent Karma History:**\n"
            for log in logs:
                symbol = "+" if log.points_change > 0 else ""
                text += f"`{log.timestamp.strftime('%Y-%m-%d %H:%M')}`: **{symbol}{log.points_change}** ({log.reason})\n"

            await ctx.respond(text, ephemeral=True)

def setup(bot):
    bot.add_cog(KarmaCog(bot))
