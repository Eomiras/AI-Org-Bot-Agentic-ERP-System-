import discord
from discord.ext import commands, tasks
from discord import option
from datetime import datetime, timedelta, timezone
from math import floor
from sqlalchemy import select, update
from bot.core.database import AsyncSessionLocal
from bot.core.models import User, BankAccount, Loan, Transaction
from bot.core.logger import logger

class IronBankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.BASE_CREDIT = 1000
        self.TRUST_FACTOR = 1000
        self.DUTY_FACTOR = 500
        self.MIN_TRUST_REQ = 80
        self.interest_loop.start()

    def cog_unload(self):
        self.interest_loop.cancel()

    def calculate_max_credit(self, user: User) -> int:
        trust = user.trust_score or 50
        duty = user.duty_score or 50
        return self.BASE_CREDIT + (trust * self.TRUST_FACTOR) + (duty * self.DUTY_FACTOR)

    loan_group = discord.SlashCommandGroup("loan", "Iron Bank Interface")

    @loan_group.command(name="request", description="Request a credit line.")
    @option("amount", description="Amount to borrow")
    async def request_loan(self, ctx: discord.ApplicationContext, amount: int):
        if amount <= 0:
            await ctx.respond("❌ Invalid amount.", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            # Fetch User & Account
            result = await session.execute(select(User).where(User.discord_id == ctx.author.id))
            user = result.scalar_one_or_none()

            if not user:
                await ctx.respond("User not found.", ephemeral=True)
                return

            # 1. Eligibility Check
            trust = user.trust_score or 50
            if trust < self.MIN_TRUST_REQ:
                await ctx.respond(f"❌ **Loan Denied.** Minimum Trust Score of {self.MIN_TRUST_REQ} required. Your Trust: {trust}.", ephemeral=True)
                return

            # 2. Check Active Loans
            loans_res = await session.execute(select(Loan).where(Loan.user_id == ctx.author.id, Loan.status == "ACTIVE"))
            if loans_res.scalar_one_or_none():
                await ctx.respond("❌ **Loan Denied.** You already have an active loan. Repay it first.", ephemeral=True)
                return

            # 3. Credit Line Check
            max_credit = self.calculate_max_credit(user)
            if amount > max_credit:
                await ctx.respond(f"❌ **Loan Denied.** Requested amount exceeds your credit line.\nMax Credit: {max_credit} NC.", ephemeral=True)
                return

            # 4. Disbursement (ACID)
            async with session.begin():
                # Get Account
                acct_res = await session.execute(select(BankAccount).where(BankAccount.user_id == ctx.author.id).with_for_update())
                account = acct_res.scalar_one_or_none()

                if not account:
                    # Create if missing
                    account = BankAccount(user_id=ctx.author.id, balance=0)
                    session.add(account)
                    await session.flush()

                # Add Balance
                account.balance += amount

                # Create Loan Contract
                due = datetime.now(timezone.utc) + timedelta(days=30)
                loan = Loan(
                    user_id=ctx.author.id,
                    amount=amount,
                    initial_amount=amount,
                    due_date=due,
                    status="ACTIVE"
                )
                session.add(loan)

                # Log
                session.add(Transaction(
                    receiver_id=ctx.author.id,
                    amount=amount,
                    reason=f"Iron Bank Disbursement (Due: {due.strftime('%Y-%m-%d')})"
                ))

            await ctx.respond(f"✅ **Loan Approved.** {amount} NC transferred to your account.\nDue Date: {due.strftime('%Y-%m-%d')}", ephemeral=True)

    @loan_group.command(name="repay", description="Repay your active loan.")
    async def repay_loan(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Find Loan
                loans_res = await session.execute(select(Loan).where(Loan.user_id == ctx.author.id, Loan.status == "ACTIVE").with_for_update())
                loan = loans_res.scalar_one_or_none()

                if not loan:
                    await ctx.respond("You have no active loans.", ephemeral=True)
                    return

                # Check Balance
                acct_res = await session.execute(select(BankAccount).where(BankAccount.user_id == ctx.author.id).with_for_update())
                account = acct_res.scalar_one_or_none()

                if not account or account.balance < loan.amount:
                    await ctx.respond(f"❌ **Insufficient Funds.** You need {loan.amount} NC to repay this loan.", ephemeral=True)
                    return

                # Repay
                account.balance -= loan.amount
                loan.status = "PAID"

                # Log
                session.add(Transaction(
                    sender_id=ctx.author.id,
                    amount=loan.amount,
                    reason=f"Loan Repayment (ID: {loan.id})"
                ))

        await ctx.respond("✅ **Loan Repaid.** Your debt is cleared. Trust Score impact: Positive.", ephemeral=True)

    @tasks.loop(hours=24)
    async def interest_loop(self):
        logger.info("💸 Iron Bank: Checking for overdue loans...")
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as session:
            # Find overdue loans
            stmt = select(Loan).where(Loan.status == "ACTIVE", Loan.due_date < now)
            result = await session.execute(stmt)
            overdue_loans = result.scalars().all()

            for loan in overdue_loans:
                # Apply Interest/Penalty
                # Simple logic: Add 5% penalty once per day overdue? Or flat fee?
                # Design says: Daily Interest.

                interest = floor(loan.amount * loan.interest_rate) # 5% default
                loan.amount += interest

                # Trust Penalty
                user_res = await session.execute(select(User).where(User.discord_id == loan.user_id))
                user = user_res.scalar_one()
                if user.trust_score and user.trust_score > 0:
                    user.trust_score -= 1 # Decay trust for bad debt

                logger.info(f"Overdue Loan {loan.id}: Added {interest} NC interest. Trust penalized.")

            if overdue_loans:
                await session.commit()

    @interest_loop.before_loop
    async def before_interest_loop(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(IronBankCog(bot))
