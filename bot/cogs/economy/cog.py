import discord
from discord.ext import commands
from sqlalchemy import select, update
from sqlalchemy.exc import NoResultFound
from datetime import datetime, timedelta, timezone
from bot.core.database import get_db, AsyncSessionLocal
from bot.core.models import BankAccount, Transaction, User
from bot.core.logger import logger

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_or_create_account(self, session, user_id: int):
        result = await session.execute(select(BankAccount).where(BankAccount.user_id == user_id))
        account = result.scalar_one_or_none()

        if not account:
            # Ensure user exists in users table first
            user_result = await session.execute(select(User).where(User.discord_id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                # Create user if not exists (minimal entry)
                user = User(discord_id=user_id)
                session.add(user)
                await session.flush() # flush to save user so FK works

            account = BankAccount(user_id=user_id, balance=0, currency_type="NC")
            session.add(account)
            await session.flush()

        return account

    @commands.command(name="balance")
    async def balance(self, ctx):
        """Shows current user balance."""
        async with AsyncSessionLocal() as session:
            account = await self.get_or_create_account(session, ctx.author.id)
            await session.commit()

            embed = discord.Embed(title="Bank Account", color=discord.Color.blue())
            embed.add_field(name="Owner", value=ctx.author.display_name, inline=False)
            embed.add_field(name="Balance", value=f"{account.balance} {account.currency_type}", inline=False)
            await ctx.send(embed=embed)

    @commands.command(name="daily")
    async def daily(self, ctx):
        """Gives free credits once per 24h."""
        async with AsyncSessionLocal() as session:
            account = await self.get_or_create_account(session, ctx.author.id)

            now = datetime.now(timezone.utc)
            if account.last_daily_claim:
                # Ensure last_daily_claim is timezone-aware
                last_claim = account.last_daily_claim
                if last_claim.tzinfo is None:
                    last_claim = last_claim.replace(tzinfo=timezone.utc)

                next_claim = last_claim + timedelta(hours=24)

                if now < next_claim:
                    remaining = next_claim - now
                    hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    await ctx.send(f"You have already claimed your daily credits. Try again in {hours}h {minutes}m.")
                    return

            amount = 100
            account.balance += amount
            account.last_daily_claim = now

            # Log transaction
            transaction = Transaction(
                receiver_id=ctx.author.id,
                amount=amount,
                reason="Daily Reward"
            )
            session.add(transaction)

            await session.commit()
            await ctx.send(f"You received **{amount} NC**! New Balance: {account.balance} NC")

    @commands.command(name="pay")
    async def pay(self, ctx, member: discord.Member, amount: int):
        """Transfers funds safely to another user."""
        if amount <= 0:
            await ctx.send("Amount must be positive.")
            return

        if member.id == ctx.author.id:
            await ctx.send("You cannot pay yourself.")
            return

        async with AsyncSessionLocal() as session:
            async with session.begin(): # Start atomic transaction
                # Sender
                sender_account = await self.get_or_create_account(session, ctx.author.id)

                if sender_account.balance < amount:
                    await ctx.send(f"Insufficient funds. You have {sender_account.balance} NC.")
                    return

                # Receiver
                receiver_account = await self.get_or_create_account(session, member.id)

                # Transfer
                sender_account.balance -= amount
                receiver_account.balance += amount

                # Record
                transaction = Transaction(
                    sender_id=ctx.author.id,
                    receiver_id=member.id,
                    amount=amount,
                    reason=f"Transfer from {ctx.author.name}"
                )
                session.add(transaction)

            # session.begin() context manager commits automatically if no exception
            await ctx.send(f"Successfully transferred **{amount} NC** to {member.mention}.")

def setup(bot):
    bot.add_cog(Economy(bot))
