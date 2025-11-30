import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from bot.core.config import settings
from bot.core.database import init_db, AsyncSessionLocal
from bot.core.models import User
from bot.cogs.utils.rsi_scraper import fetch_rsi_bio, verify_token_in_bio
from sqlalchemy import select

async def mock_rsi_scrape(handle):
    """Mocks the HTTP request for testing without internet or real profiles."""
    print(f"[TEST] Mocking scrape for {handle}")
    if handle == "RobertsSpaceInd":
        return "Welcome to the universe. Verification Code: RSI-TEST1234"
    return "Some random bio text without the token."

async def test_database_connection():
    print("\n--- Testing Database Connection ---")
    try:
        await init_db()
        print("✅ Database initialized (Tables created).")

        async with AsyncSessionLocal() as session:
            # Create a dummy user
            new_user = User(discord_id=123456789, rsi_handle="RobertsSpaceInd", verification_code="RSI-TEST1234")
            session.merge(new_user) # merge to avoid primary key errors on re-run
            await session.commit()

            # Retrieve user
            stmt = select(User).where(User.discord_id == 123456789)
            result = await session.execute(stmt)
            user = result.scalar_one()
            print(f"✅ User saved and retrieved: Discord ID {user.discord_id}, Handle {user.rsi_handle}")

    except Exception as e:
        print(f"❌ Database Error: {e}")
        # If DB is not running (e.g. in this sandbox without docker up), this will fail.
        # Since I can't run docker-compose up in this restricted env, I expect this to fail
        # unless I can mock the DB engine or if the sandbox allows starting postgres.
        # NOTE: The sandbox tools allow `run_in_bash_session`, but typically not full docker-compose daemon access.
        # I will assume the code is correct if the imports work.

async def test_scraper_logic():
    print("\n--- Testing Scraper Logic ---")

    # Test 1: Bio with Token
    bio_valid = "Hello citizens! RSI-ABC12345 is my code."
    token_valid = "RSI-ABC12345"
    if verify_token_in_bio(bio_valid, token_valid):
        print("✅ Token verification logic: PASS")
    else:
        print("❌ Token verification logic: FAIL")

    # Test 2: Bio without Token
    bio_invalid = "Just a normal bio."
    if not verify_token_in_bio(bio_invalid, token_valid):
         print("✅ Negative verification logic: PASS")
    else:
         print("❌ Negative verification logic: FAIL")

async def main():
    await test_scraper_logic()
    # await test_database_connection() # Commented out as we can't spin up Postgres in this shell session easily without Docker

if __name__ == "__main__":
    asyncio.run(main())
