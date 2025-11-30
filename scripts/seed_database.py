import asyncio
import os
import sys
from sqlalchemy import select

# Add project root
sys.path.append(os.getcwd())

from bot.core.database import AsyncSessionLocal, init_db
from bot.core.models import User, BankAccount, ReputationRank

# --- GENESIS CONFIGURATION ---
INITIAL_TREASURY_BALANCE = 1_000_000
TREASURY_ID = 999999999001 # Special ID for Treasury
ESCROW_ID = 999999999002   # Special ID for Escrow

RANKS = [
    {"name": "Initiate", "min_reputation": 0, "salary": 10},
    {"name": "Citizen", "min_reputation": 100, "salary": 50},
    {"name": "Veteran", "min_reputation": 500, "salary": 100},
    {"name": "Officer", "min_reputation": 1000, "salary": 250},
    {"name": "High Command", "min_reputation": 5000, "salary": 1000},
]

async def seed_genesis():
    print("--- 🌌 INITIATING GENESIS SEEDING ---")

    # Ensure DB tables exist
    await init_db()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. Check for existing Treasury (Double-Seeding Guard)
            stmt = select(BankAccount).where(BankAccount.user_id == TREASURY_ID)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                print("⚠️  Genesis Block already exists. Aborting Seeding.")
                return

            print("🌱 Seeding Treasury...")
            # We need a User entity for the FK constraint usually, depending on how strict.
            # Yes, BankAccount.user_id FK references User.discord_id.
            # So we must create "System Users" first.

            system_users = [
                User(discord_id=TREASURY_ID, rsi_handle="ORG_TREASURY", is_verified=True),
                User(discord_id=ESCROW_ID, rsi_handle="ORG_ESCROW", is_verified=True)
            ]
            session.add_all(system_users)
            await session.flush() # Flush to make IDs available (though we set them manually)

            # Create Accounts
            treasury = BankAccount(
                user_id=TREASURY_ID,
                balance=INITIAL_TREASURY_BALANCE,
                account_type="TREASURY"
            )
            escrow = BankAccount(
                user_id=ESCROW_ID,
                balance=0,
                account_type="ESCROW"
            )
            session.add_all([treasury, escrow])

            print("🌱 Seeding Ranks...")
            for rank_data in RANKS:
                rank = ReputationRank(
                    name=rank_data["name"],
                    min_reputation=rank_data["min_reputation"],
                    salary=rank_data["salary"]
                )
                session.add(rank)

            print("✅ Genesis Data Staged.")

        # Commit happens automatically on exit of session.begin() if no error
        print("✅ GENESIS EVENT COMPLETE. Core Ledger is Balanced.")

if __name__ == "__main__":
    # In a real environment, we'd load env vars here if needed
    asyncio.run(seed_genesis())
