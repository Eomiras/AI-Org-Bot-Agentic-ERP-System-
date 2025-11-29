import discord
from discord.ext import commands
from discord import ui
import secrets
import string

from sqlalchemy import select
from bot.core.database import AsyncSessionLocal
from bot.core.models import User
from bot.cogs.utils.rsi_scraper import fetch_rsi_bio, verify_token_in_bio
from bot.core.logger import logger

class AuthView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Start Verification", style=discord.ButtonStyle.primary, custom_id="start_verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: ui.Button):
        # Create a modal for inputting the Handle
        await interaction.response.send_modal(RSIHandleModal())

class RSIHandleModal(ui.Modal, title="RSI Account Verification"):
    handle = ui.TextInput(label="RSI Handle", placeholder="YourExactHandleName", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        handle_text = self.handle.value.strip()

        # Generate a random token
        token = "RSI-" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

        # Save to DB
        async with AsyncSessionLocal() as session:
            # Check if user exists
            result = await session.execute(select(User).where(User.discord_id == interaction.user.id))
            user = result.scalar_one_or_none()

            if not user:
                user = User(discord_id=interaction.user.id)
                session.add(user)

            user.rsi_handle = handle_text
            user.verification_code = token
            user.is_verified = False

            await session.commit()

        embed = discord.Embed(title="Verification Step 2", color=discord.Color.yellow())
        embed.description = (
            f"1. Go to your [RSI Profile](https://robertsspaceindustries.com/account/profile)\n"
            f"2. Add the following code to your **Bio / Short Bio**:\n"
            f"```\n{token}\n```\n"
            f"3. Save your profile.\n"
            f"4. Run `/check` or click the button below."
        )

        view = CheckView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class CheckView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Check Verification", style=discord.ButtonStyle.success)
    async def check_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.discord_id == interaction.user.id))
            user = result.scalar_one_or_none()

            if not user or not user.verification_code:
                await interaction.followup.send("No pending verification found. Please start over.", ephemeral=True)
                return

            # Scrape
            bio = await fetch_rsi_bio(user.rsi_handle)

            if bio is None:
                await interaction.followup.send(f"Could not fetch profile for `{user.rsi_handle}`. Is the handle correct? Does the page exist?", ephemeral=True)
                return

            if verify_token_in_bio(bio, user.verification_code):
                user.is_verified = True
                user.verification_code = None # Clear code
                await session.commit()

                await interaction.followup.send(f"✅ Success! Your RSI handle `{user.rsi_handle}` has been verified.", ephemeral=True)
                # Here we could assign roles
            else:
                await interaction.followup.send(f"❌ Token not found in bio. \n**Found Bio:**\n> {bio}\n\nPlease make sure you saved the profile and try again.", ephemeral=True)


class Authentication(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="verify")
    async def verify(self, ctx):
        """Starts the verification process."""
        embed = discord.Embed(title="Identity Verification", description="Click below to link your RSI account.")
        await ctx.send(embed=embed, view=AuthView())

    @commands.command(name="check")
    async def check(self, ctx):
        """Manually checks verification status."""
        # Logic similar to button, but command based
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.discord_id == ctx.author.id))
            user = result.scalar_one_or_none()

            if not user or not user.verification_code:
                await ctx.reply("You have no pending verification.")
                return

            msg = await ctx.reply("Checking RSI Profile...")

            bio = await fetch_rsi_bio(user.rsi_handle)
            if bio and verify_token_in_bio(bio, user.verification_code):
                user.is_verified = True
                user.verification_code = None
                await session.commit()
                await msg.edit(content=f"✅ Verified as `{user.rsi_handle}`!")
            else:
                await msg.edit(content="❌ Verification failed. Token not found.")

def setup(bot):
    bot.add_cog(Authentication(bot))
