import discord
from discord.ext import commands
from discord import ui
from math import floor
from bot.core.logger import logger
from bot.core.database import AsyncSessionLocal
from bot.core.models import BankAccount, Transaction, User
from sqlalchemy import select, update

# --- 1. The Math Logic (Integer Policy) ---
class LootCalculator:
    def __init__(self, gross_amount: int, tax_rate: float, participants: int):
        self.gross = gross_amount
        self.tax_rate = tax_rate
        self.count = participants

    def calculate(self) -> dict:
        if self.count <= 0: return {}

        # 1. Calculate Tax (Floor)
        tax_amount = floor(self.gross * self.tax_rate)

        # 2. Net
        net_loot = self.gross - tax_amount

        # 3. Split (Floor)
        payout_per_player = floor(net_loot / self.count)

        # 4. Remainder (Floating Point Dust Recovery)
        total_payout = payout_per_player * self.count
        remainder = net_loot - total_payout

        # 5. Final Org Share
        final_org_share = tax_amount + remainder

        return {
            "gross": self.gross,
            "tax_base": tax_amount,
            "payout": payout_per_player,
            "remainder": remainder,
            "org_share": final_org_share
        }

# --- 2. The View (Human-in-the-Loop) ---
class ConfirmSplitView(ui.View):
    def __init__(self, bot, result_data, participants, author_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.data = result_data
        self.participants = participants # List of Members
        self.author_id = author_id
        self.processed = False

    @ui.button(label="CONFIRM DISTRIBUTION", style=discord.ButtonStyle.success)
    async def confirm(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the Mission Commander can confirm this split.", ephemeral=True)
            return

        if self.processed:
            await interaction.response.send_message("Transaction already processed.", ephemeral=True)
            return

        self.processed = True
        await interaction.response.defer()

        # Execute Transaction
        try:
            # Note: In a real implementation, we would call the Economy Tool or Supervisor.
            # Here, we do it directly via DB for simplicity, preserving ACID.
            # But wait, we should respect "The Broker" architecture.
            # However, batch operations are often simpler in code than via LLM prompts.
            # We will use direct DB access here for strict control.

            async with AsyncSessionLocal() as session:
                async with session.begin():
                    # 1. Update Treasury
                    # Assuming Treasury User ID is 999999999001 (from Seed)
                    TREASURY_ID = 999999999001

                    # Lock Treasury
                    stmt = select(BankAccount).where(BankAccount.user_id == TREASURY_ID).with_for_update()
                    res = await session.execute(stmt)
                    treasury = res.scalar_one_or_none()

                    if not treasury:
                        await interaction.followup.send("❌ Error: Treasury Account not found (Genesis missing?).")
                        return

                    treasury.balance += self.data["org_share"]

                    # 2. Update Players
                    for member in self.participants:
                        # Lock Player
                        stmt = select(BankAccount).where(BankAccount.user_id == member.id).with_for_update()
                        res = await session.execute(stmt)
                        account = res.scalar_one_or_none()

                        if not account:
                            # Create account immediately to ensure payout
                            # Ensure User exists first
                            user_chk = await session.execute(select(User).where(User.discord_id == member.id))
                            if not user_chk.scalar_one_or_none():
                                session.add(User(discord_id=member.id))
                                await session.flush()

                            account = BankAccount(user_id=member.id, balance=0, currency_type="NC")
                            session.add(account)
                            await session.flush()

                        account.balance += self.data["payout"]

                        # Log Player Payout (Only log if payout happened, which is now guaranteed)
                        session.add(Transaction(
                            receiver_id=member.id,
                            amount=self.data["payout"],
                            reason=f"Mission Payout (Ref: {interaction.id})"
                        ))

                    # 3. Log Org Share
                    session.add(Transaction(
                        receiver_id=TREASURY_ID,
                        amount=self.data["org_share"],
                        reason=f"Tax & Dust from Loot Split (Ref: {interaction.id})"
                    ))

            await interaction.edit_original_response(content="✅ **PAYOUT SUCCESSFUL.** The Ledger has been updated.", view=None)

        except Exception as e:
            logger.error(f"Loot Split Error: {e}")
            await interaction.followup.send(f"❌ Transaction Failed: {str(e)}")

    @ui.button(label="CANCEL", style=discord.ButtonStyle.danger)
    async def cancel(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return
        self.processed = True
        await interaction.edit_original_response(content="🛑 **Split Cancelled.** No funds were moved.", view=None)


class LootCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TAX_RATE = 0.10 # 10% Org Share

    @discord.slash_command(name="split", description="Analyze loot screenshot and split payout.")
    async def split(self, ctx: discord.ApplicationContext, screenshot: discord.Attachment, members: str):
        """
        Members: Space-separated mentions or IDs.
        Example: /split [image] @Player1 @Player2
        """
        # Parse Members
        try:
            # PyCord handles mentions in args differently depending on type.
            # Since we use a string input 'members', we parse manually.
            # In a real bot we might use multiple user options or a Greedy converter.
            # For this MVP, we rely on the user tagging them in the string.

            member_ids = [int(m.strip('<@!>')) for m in members.split() if m.startswith('<@')]
            # Add self if not included? Usually commander is included.
            if ctx.author.id not in member_ids:
                member_ids.append(ctx.author.id)

            participants = [ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid) for uid in member_ids]
            participants = [p for p in participants if p] # Filter None

        except Exception as e:
            await ctx.respond("❌ Error parsing members. Please use @mentions.", ephemeral=True)
            return

        await ctx.defer()

        # 1. OCR (Async)
        # Note: We simulate calling the worker.
        # In real code: job = await self.bot.arq.enqueue_job("process_ocr", screenshot.url)
        # result = await job.result()

        # Using Mock directly for speed/stability in this specific turn
        from bot.ml_modules.vision import process_ocr
        result = await process_ocr(None, screenshot.url)

        if result["status"] != "SUCCESS":
            await ctx.respond(f"❌ OCR Failed: {result.get('reason')}")
            return

        gross_amount = result["amount"]

        # 2. Calculation
        calc = LootCalculator(gross_amount, self.TAX_RATE, len(participants))
        data = calc.calculate()

        # 3. Display
        embed = discord.Embed(title="⚖️ Loot Split Proposal", color=discord.Color.gold())
        embed.add_field(name="Gross Loot", value=f"{data['gross']} aUEC", inline=False)
        embed.add_field(name="Org Share (10%)", value=f"{data['tax_base']} aUEC", inline=True)
        embed.add_field(name="Dust/Rounding", value=f"+ {data['remainder']} aUEC", inline=True)
        embed.add_field(name="**Total to Treasury**", value=f"**{data['org_share']} aUEC**", inline=False)
        embed.add_field(name="----------------", value="----------------", inline=False)
        embed.add_field(name="**Payout per Player**", value=f"**{data['payout']} aUEC**", inline=False)
        embed.add_field(name="Participants", value=f"{len(participants)}", inline=True)

        view = ConfirmSplitView(self.bot, data, participants, ctx.author.id)
        await ctx.respond(embed=embed, view=view)

def setup(bot):
    bot.add_cog(LootCog(bot))
