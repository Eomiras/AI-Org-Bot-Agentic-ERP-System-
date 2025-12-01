import discord
from discord.ext import commands
from bot.core.logger import logger

class Media(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="scan_loot", description="Scan loot from an image")
    async def scan_loot(self, ctx: discord.ApplicationContext, image: discord.Attachment):
        """
        Scans an image attachment for loot data.
        """
        logger.info(f"User {ctx.author} requested scan_loot for {image.url}")

        # Enqueue the job to the worker
        # Note: self.bot.arq must be initialized in the main bot setup
        try:
            await self.bot.arq.enqueue_job("process_ocr", image.url)
            await ctx.respond(f"✅ Scanning job enqueued for: {image.filename}\nWe will notify you when processing is complete.", ephemeral=True)
        except AttributeError:
            logger.error("Arq worker pool not initialized in bot.")
            await ctx.respond("❌ Internal Error: Worker system not initialized.", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to enqueue job: {e}")
            await ctx.respond("❌ Failed to queue the job. Please try again later.", ephemeral=True)

def setup(bot):
    bot.add_cog(Media(bot))
