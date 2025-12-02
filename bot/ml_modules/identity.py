import os
import logging
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from bot.core.database import AsyncSessionLocal
from bot.core.models import User, ReputationRank
from bot.core.security import decrypt_pii

logger = logging.getLogger(__name__)

async def generate_id_card_task(ctx, user_id: int) -> str:
    """
    Worker Task: Generates an ID Card image for a user.
    """
    logger.info(f"Generating ID Card for user {user_id}")

    # 1. Fetch Data
    user_data = {}
    async with AsyncSessionLocal() as session:
        # Fetch User
        result = await session.execute(select(User).where(User.discord_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return "ERROR: User not found."

        if not user.is_verified:
            return "ERROR: User not verified. ID Card denied."

        # Decrypt PII
        rsi_handle = "UNKNOWN"
        if user.pii_blob:
            try:
                rsi_handle = decrypt_pii(user.discord_id, user.pii_blob)
            except Exception as e:
                logger.error(f"Decryption failed for {user_id}: {e}")
                rsi_handle = "DECRYPT_FAIL"

        # Determine Rank (Mock logic for now, or fetch from reputation)
        # We don't have a direct link between User and Rank table yet in models,
        # usually it's calculated. For now, we assume "Citizen".
        rank_name = "Citizen"

        user_data = {
            "handle": rsi_handle,
            "id": str(user.discord_id),
            "rank": rank_name,
            "verified": "VERIFIED" if user.is_verified else "PENDING"
        }

    # 2. Draw Image (Cyberpunk Style)
    try:
        width, height = 600, 300
        # Background: Dark Blue/Grey
        img = Image.new('RGB', (width, height), color=(10, 15, 30))
        draw = ImageDraw.Draw(img)

        # Border
        draw.rectangle([(10, 10), (width-10, height-10)], outline=(0, 255, 255), width=3)

        # Header
        draw.rectangle([(10, 10), (width-10, 60)], fill=(0, 50, 50))
        draw.text((20, 20), "STAR CITIZEN ORG IDENTITY", fill=(0, 255, 255)) # Default font

        # Data Fields
        # We assume default font for simplicity in sandbox.
        # In prod, we would load a .ttf file.

        # Handle (Large)
        draw.text((30, 80), f"HANDLE: {user_data['handle']}", fill=(255, 255, 255))

        # Rank
        draw.text((30, 130), f"RANK: {user_data['rank']}", fill=(200, 200, 200))

        # ID
        draw.text((30, 180), f"ID: {user_data['id']}", fill=(100, 100, 100))

        # Status
        draw.text((450, 250), user_data['verified'], fill=(0, 255, 0))

        # 3. Save
        output_dir = "data/temp/id_cards"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"id_{user_id}.png"
        path = os.path.join(output_dir, filename)

        img.save(path)
        logger.info(f"ID Card saved to {path}")

        return path

    except Exception as e:
        logger.error(f"Image Generation Error: {e}")
        return f"ERROR: Generation failed - {str(e)}"
