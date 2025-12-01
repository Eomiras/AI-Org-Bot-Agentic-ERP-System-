import discord
from discord.ext import commands
from discord import option
from sqlalchemy import select
from math import floor
from bot.core.database import AsyncSessionLocal
from bot.core.models import User, BankAccount, Company, Shareholder, Transaction
from bot.core.logger import logger

class StockMarketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.REGISTRATION_FEE = 50_000

    company_group = discord.SlashCommandGroup("company", "Company Management")
    stock_group = discord.SlashCommandGroup("stock", "Stock Market")

    @company_group.command(name="register", description="Register a new Company (Cost: 50,000 NC).")
    @option("name", description="Company Name")
    async def register(self, ctx: discord.ApplicationContext, name: str):
        await ctx.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Check Name
                existing = await session.execute(select(Company).where(Company.name == name))
                if existing.scalar_one_or_none():
                    await ctx.respond("❌ Name already taken.", ephemeral=True)
                    return

                # Lock User Account
                stmt = select(BankAccount).where(BankAccount.user_id == ctx.author.id).with_for_update()
                user_acc = (await session.execute(stmt)).scalar_one_or_none()

                if not user_acc or user_acc.balance < self.REGISTRATION_FEE:
                    await ctx.respond(f"❌ Insufficient Funds. Fee: {self.REGISTRATION_FEE} NC.", ephemeral=True)
                    return

                # Deduct Fee
                user_acc.balance -= self.REGISTRATION_FEE

                # Create Company
                # We need to get the ID. Auto-increment is tricky in async add.
                # We create Company first, flush, then create Account.

                company = Company(
                    name=name,
                    ceo_id=ctx.author.id,
                    share_price=100,
                    total_shares=1000,
                    bank_account_id=0 # Placeholder
                )
                session.add(company)
                await session.flush() # Get ID

                # Assign Bank Account ID (Negative Company ID)
                # We need to ensure the User table supports negative IDs or check FK constraints.
                # In our schema, BankAccount.user_id FKs to User.discord_id.
                # So we must create a User record for the company.
                company_user_id = -company.id

                session.add(User(discord_id=company_user_id, rsi_handle=f"CORP_{company.id}", is_verified=True))
                await session.flush()

                comp_acc = BankAccount(user_id=company_user_id, balance=0, account_type="COMPANY")
                session.add(comp_acc)

                company.bank_account_id = company_user_id

                # Assign CEO all shares
                shareholder = Shareholder(user_id=ctx.author.id, company_id=company.id, shares_owned=1000)
                session.add(shareholder)

                # Audit
                session.add(Transaction(
                    sender_id=ctx.author.id,
                    receiver_id=999999999001, # Treasury (Fee Burn or Tax?) Let's burn/fee it to Treasury.
                    amount=self.REGISTRATION_FEE,
                    reason=f"Company Registration: {name}"
                ))

        await ctx.respond(f"✅ **Company Registered:** {name}\nCEO: {ctx.author.mention}\nAccount ID: {company_user_id}", ephemeral=True)

    @company_group.command(name="dividend", description="Pay out dividends to shareholders.")
    @option("amount", description="Total amount to distribute")
    async def dividend(self, ctx: discord.ApplicationContext, amount: int):
        if amount <= 0: return
        await ctx.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Fetch Company
                stmt = select(Company).where(Company.ceo_id == ctx.author.id)
                res = await session.execute(stmt)
                company = res.scalar_one_or_none()

                if not company:
                    await ctx.respond("❌ You are not a CEO of any company.", ephemeral=True)
                    return

                # Lock Company Account
                comp_acc_stmt = select(BankAccount).where(BankAccount.user_id == company.bank_account_id).with_for_update()
                comp_acc = (await session.execute(comp_acc_stmt)).scalar_one_or_none()

                if not comp_acc or comp_acc.balance < amount:
                    await ctx.respond("❌ Insufficient Corporate Funds.", ephemeral=True)
                    return

                # Distribute
                comp_acc.balance -= amount

                # Fetch Shareholders
                holders_stmt = select(Shareholder).where(Shareholder.company_id == company.id)
                shareholders = (await session.execute(holders_stmt)).scalars().all()

                payout_log = []
                for holder in shareholders:
                    # Calculate Share
                    share_fraction = holder.shares_owned / company.total_shares
                    payout = floor(amount * share_fraction)

                    if payout > 0:
                        # Lock User Account
                        u_acc_stmt = select(BankAccount).where(BankAccount.user_id == holder.user_id).with_for_update()
                        u_acc = (await session.execute(u_acc_stmt)).scalar_one_or_none()

                        if u_acc:
                            u_acc.balance += payout
                            payout_log.append(f"<@{holder.user_id}>: {payout}")

                # Log
                session.add(Transaction(
                    sender_id=company.bank_account_id,
                    receiver_id=ctx.author.id, # Just referencing CEO for log context
                    amount=amount,
                    reason=f"Dividend Payout: {company.name}"
                ))

        await ctx.respond(f"✅ **Dividends Distributed.**\nTotal: {amount} NC", ephemeral=True)

    @stock_group.command(name="buy", description="Invest in a company.")
    @option("company_name", description="Name of company")
    @option("shares", description="Number of shares")
    async def buy_stock(self, ctx: discord.ApplicationContext, company_name: str, shares: int):
        # Implementation of buying new shares (Capital Increase)
        # Money goes to Company. Shares are minted.
        if shares <= 0: return
        await ctx.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                company_res = await session.execute(select(Company).where(Company.name == company_name))
                company = company_res.scalar_one_or_none()

                if not company:
                    await ctx.respond("Company not found.", ephemeral=True)
                    return

                cost = shares * company.share_price

                # Lock User
                user_acc = (await session.execute(select(BankAccount).where(BankAccount.user_id == ctx.author.id).with_for_update())).scalar_one_or_none()
                if not user_acc or user_acc.balance < cost:
                    await ctx.respond(f"Insufficient funds. Cost: {cost} NC.", ephemeral=True)
                    return

                # Lock Company
                comp_acc = (await session.execute(select(BankAccount).where(BankAccount.user_id == company.bank_account_id).with_for_update())).scalar_one_or_none()

                # Transfer
                user_acc.balance -= cost
                comp_acc.balance += cost

                # Update/Create Shareholder record
                holder_stmt = select(Shareholder).where(Shareholder.user_id == ctx.author.id, Shareholder.company_id == company.id)
                holder = (await session.execute(holder_stmt)).scalar_one_or_none()

                if holder:
                    holder.shares_owned += shares
                else:
                    holder = Shareholder(user_id=ctx.author.id, company_id=company.id, shares_owned=shares)
                    session.add(holder)

                company.total_shares += shares

                session.add(Transaction(
                    sender_id=ctx.author.id,
                    receiver_id=company.bank_account_id,
                    amount=cost,
                    reason=f"Stock Purchase: {shares} shares of {company.name}"
                ))

        await ctx.respond(f"✅ Purchased {shares} shares of **{company.name}** for {cost} NC.", ephemeral=True)

def setup(bot):
    bot.add_cog(StockMarketCog(bot))
