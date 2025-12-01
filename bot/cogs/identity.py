import discord
from discord.ext import commands
import asyncio
import os
from bot.core.logger import logger

class IdentityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="idcard", description="Generate your official Organization ID Card.")
    async def idcard(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True) # Ephemeral to protect privacy (DM delivery)

        # 1. Enqueue Job
        try:
            job = await self.bot.arq.enqueue_job("generate_id_card_task", ctx.author.id)

            # 2. Wait for result (Short TTL)
            path = await job.result(timeout=10, poll_delay=0.5)

            if path.startswith("ERROR"):
                await ctx.respond(f"❌ Generation Failed: {path}", ephemeral=True)
                return

            if not os.path.exists(path):
                await ctx.respond("❌ Internal Error: Image file missing.", ephemeral=True)
                return

            # 3. Send via DM
            try:
                file = discord.File(path, filename="org_id_card.png")
                await ctx.author.send("🛡️ **SHIELD OPERATOR:** Identity Asset generated. Secure delivery.", file=file)
                await ctx.respond("✅ ID Card sent to your DMs.", ephemeral=True)
            except discord.Forbidden:
                await ctx.respond("❌ I cannot DM you. Please enable DMs.", ephemeral=True)
            finally:
                # 4. Cleanup (Privacy Guard)
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Cleaned up ID card {path}")

        except asyncio.TimeoutError:
            await ctx.respond("❌ Generation timed out.", ephemeral=True)
        except Exception as e:
            logger.error(f"ID Card Error: {e}")
            await ctx.respond("❌ An error occurred.", ephemeral=True)

def setup(bot):
    bot.add_cog(IdentityCog(bot))
