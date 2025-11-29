import discord
from discord.ext import commands
import asyncio
import os
from bot.core.config import settings
from bot.core.logger import setup_logging, logger
from bot.core.database import init_db

setup_logging()

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class OrgBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # Initialize DB
        logger.info("Initializing Database...")
        await init_db()

        # Load Cogs
        extensions = [
            "bot.cogs.authentication",
        ]

        for ext in extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Loaded extension: {ext}")
            except Exception as e:
                logger.error(f"Failed to load extension {ext}", error=str(e))

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("------")

def main():
    bot = OrgBot()

    if not settings.DISCORD_TOKEN or settings.DISCORD_TOKEN == "your_discord_token_here":
        logger.error("DISCORD_TOKEN not set in .env")
        return

    bot.run(settings.DISCORD_TOKEN)

if __name__ == "__main__":
    main()
