import discord
from discord.ext import commands
from discord import option
from sqlalchemy import select
from bot.core.database import AsyncSessionLocal
from bot.core.models import User, BankAccount, Bounty, Transaction
from bot.core.logger import logger

ESCROW_ID = 999999999002

class BountyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    bounty_group = discord.SlashCommandGroup("bounty", "Bounty Board & Escrow")

    @bounty_group.command(name="create", description="Post a bounty and escrow the reward.")
    @option("target", description="Target Name or Description")
    @option("reward", description="Reward Amount")
    async def create(self, ctx: discord.ApplicationContext, target: str, reward: int):
        if reward <= 0:
            await ctx.respond("Reward must be positive.", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Lock Issuer Account
                stmt = select(BankAccount).where(BankAccount.user_id == ctx.author.id).with_for_update()
                issuer_acc = (await session.execute(stmt)).scalar_one_or_none()

                if not issuer_acc or issuer_acc.balance < reward:
                    await ctx.respond(f"❌ Insufficient Funds. Balance: {issuer_acc.balance if issuer_acc else 0} NC.", ephemeral=True)
                    return

                # Lock Escrow Account
                stmt = select(BankAccount).where(BankAccount.user_id == ESCROW_ID).with_for_update()
                escrow_acc = (await session.execute(stmt)).scalar_one_or_none()

                if not escrow_acc:
                    await ctx.respond("❌ Critical Error: Escrow Account missing.", ephemeral=True)
                    return

                # Transfer to Escrow
                issuer_acc.balance -= reward
                escrow_acc.balance += reward

                # Create Bounty Record
                bounty = Bounty(
                    issuer_id=ctx.author.id,
                    target=target,
                    reward=reward,
                    status="OPEN"
                )
                session.add(bounty)

                # Audit Log
                session.add(Transaction(
                    sender_id=ctx.author.id,
                    receiver_id=ESCROW_ID,
                    amount=reward,
                    reason=f"Escrow Deposit for Bounty '{target}'"
                ))

        await ctx.respond(f"✅ **Bounty Posted.** {reward} NC moved to Escrow.\nTarget: {target}", ephemeral=True)

    @bounty_group.command(name="board", description="View open bounties.")
    async def board(self, ctx: discord.ApplicationContext):
        async with AsyncSessionLocal() as session:
            stmt = select(Bounty).where(Bounty.status == "OPEN").limit(10)
            bounties = (await session.execute(stmt)).scalars().all()

            if not bounties:
                await ctx.respond("📭 No open bounties.", ephemeral=True)
                return

            embed = discord.Embed(title="📜 Bounty Board", color=discord.Color.dark_red())
            for b in bounties:
                embed.add_field(
                    name=f"ID: {b.id} | Reward: {b.reward} NC",
                    value=f"**Target:** {b.target}\n*Issuer: <@{b.issuer_id}>*",
                    inline=False
                )

            await ctx.respond(embed=embed)

    @bounty_group.command(name="claim", description="Accept a bounty contract.")
    @option("bounty_id", description="ID of the bounty")
    async def claim(self, ctx: discord.ApplicationContext, bounty_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(Bounty).where(Bounty.id == bounty_id).with_for_update()
            bounty = (await session.execute(stmt)).scalar_one_or_none()

            if not bounty:
                await ctx.respond("Bounty not found.", ephemeral=True)
                return

            if bounty.status != "OPEN":
                await ctx.respond(f"Bounty is {bounty.status}.", ephemeral=True)
                return

            if bounty.issuer_id == ctx.author.id:
                await ctx.respond("You cannot claim your own bounty.", ephemeral=True)
                return

            bounty.status = "CLAIMED"
            bounty.hunter_id = ctx.author.id
            await session.commit()

        await ctx.respond(f"✅ You have claimed Bounty #{bounty_id}. Good hunting.", ephemeral=True)

    @bounty_group.command(name="complete", description="Confirm completion and release funds (Issuer Only).")
    @option("bounty_id", description="ID of the bounty")
    async def complete(self, ctx: discord.ApplicationContext, bounty_id: int):
        await ctx.defer(ephemeral=True)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Lock Bounty
                stmt = select(Bounty).where(Bounty.id == bounty_id).with_for_update()
                bounty = (await session.execute(stmt)).scalar_one_or_none()

                if not bounty:
                    await ctx.respond("Bounty not found.", ephemeral=True)
                    return

                if ctx.author.id != bounty.issuer_id:
                    await ctx.respond("❌ Only the Issuer can confirm completion.", ephemeral=True)
                    return

                if bounty.status != "CLAIMED":
                    await ctx.respond("Bounty must be CLAIMED before completion.", ephemeral=True)
                    return

                # Lock Escrow & Hunter
                escrow_stmt = select(BankAccount).where(BankAccount.user_id == ESCROW_ID).with_for_update()
                escrow_acc = (await session.execute(escrow_stmt)).scalar_one_or_none()

                # Ensure Hunter Account exists
                hunter_stmt = select(BankAccount).where(BankAccount.user_id == bounty.hunter_id).with_for_update()
                hunter_acc = (await session.execute(hunter_stmt)).scalar_one_or_none()

                if not hunter_acc:
                    # Create on fly logic (simplified for brevity, relying on user existence check usually)
                    # For safety, we assume hunter exists if they claimed it via interaction
                    # But we need BankAccount
                    hunter_acc = BankAccount(user_id=bounty.hunter_id, balance=0)
                    session.add(hunter_acc)
                    await session.flush()

                # Transfer
                if escrow_acc.balance < bounty.reward:
                    await ctx.respond("CRITICAL: Escrow insolvency.", ephemeral=True)
                    return # Should not happen if ACID is strictly followed

                escrow_acc.balance -= bounty.reward
                hunter_acc.balance += bounty.reward

                bounty.status = "COMPLETED"

                session.add(Transaction(
                    sender_id=ESCROW_ID,
                    receiver_id=bounty.hunter_id,
                    amount=bounty.reward,
                    reason=f"Bounty Payout #{bounty.id}"
                ))

        await ctx.respond(f"✅ **Contract Closed.** Funds released to <@{bounty.hunter_id}>.", ephemeral=True)

def setup(bot):
    bot.add_cog(BountyCog(bot))
