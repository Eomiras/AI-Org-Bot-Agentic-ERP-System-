import discord
from discord.ext import commands
from discord import option
import json
import io
from datetime import datetime

from sqlalchemy import select
from bot.core.database import AsyncSessionLocal
from bot.core.models import User
from bot.core.security import decrypt_pii
from bot.core.logger import logger

class Compliance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="privacy_export", description="Generates a JSON export of your stored data and sends it via DM.")
    async def privacy_export(self, ctx: discord.ApplicationContext):
        # Note: In PyCord, ctx is ApplicationContext for slash commands, which behaves like Context but also has interaction
        await ctx.defer(ephemeral=True) # Defer because DB + Decryption might take >3s

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.discord_id == ctx.author.id))
            user = result.scalar_one_or_none()

            if not user:
                await ctx.followup.send("No data found for your account.", ephemeral=True)
                return

            # Prepare data
            data = {
                "discord_id": user.discord_id,
                "rsi_handle": user.rsi_handle,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "consent_given": user.consent_given,
                "pii_data": None
            }

            if user.pii_blob:
                try:
                    decrypted_content = decrypt_pii(user.discord_id, user.pii_blob)
                    # Try to parse as JSON if possible, otherwise string
                    try:
                        data["pii_data"] = json.loads(decrypted_content)
                    except json.JSONDecodeError:
                        data["pii_data"] = decrypted_content
                except Exception as e:
                    logger.error(f"Failed to decrypt PII for user {user.discord_id}", error=str(e))
                    data["pii_data"] = "ERROR: Could not decrypt data."

            # Create file
            report_str = json.dumps(data, indent=4, ensure_ascii=False)
            file = discord.File(io.StringIO(report_str), filename=f"privacy_export_{ctx.author.id}.json")

            try:
                await ctx.author.send(
                    content="Here is your requested data export (GDPR Art. 15).",
                    file=file
                )
                await ctx.followup.send("✅ I have sent your data export to your DMs.", ephemeral=True)
            except discord.Forbidden:
                await ctx.followup.send("❌ I could not DM you. Please enable Direct Messages from server members and try again.", ephemeral=True)
            except Exception as e:
                logger.error(f"Error sending privacy export to {ctx.author.id}", error=str(e))
                await ctx.followup.send("❌ An error occurred while sending your data.", ephemeral=True)

    @discord.slash_command(name="privacy_forget", description="Deletes your personal information (GDPR Art. 17). This action is irreversible.")
    async def privacy_forget(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.discord_id == ctx.author.id))
            user = result.scalar_one_or_none()

            if not user:
                await ctx.followup.send("No data found to delete.", ephemeral=True)
                return

            # Anonymize/Delete Data
            user.rsi_handle = None
            user.pii_blob = None
            user.is_verified = False
            user.verification_code = None
            user.consent_given = False

            # Keep discord_id as per requirements

            await session.commit()

            logger.info(f"User {ctx.author.id} executed privacy_forget.")

            await ctx.followup.send("✅ Your personal data (RSI Handle, PII) has been deleted from our records. Your Discord ID has been retained for moderation purposes.", ephemeral=True)

def setup(bot):
    bot.add_cog(Compliance(bot))
