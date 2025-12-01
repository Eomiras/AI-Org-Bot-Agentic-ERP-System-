import asyncio
import os
import sys
import json
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

async def verify_feedback_loop():
    print("--- 📡 Verifying Feedback Loop ---")

    # 1. Mock Redis
    mock_redis = MagicMock()
    mock_pubsub = MagicMock()

    # Mock Subscribe
    mock_redis.pubsub.return_value = mock_pubsub
    mock_pubsub.subscribe = AsyncMock()

    # Mock Listen (Yield one message then stop)
    async def mock_listen():
        yield {
            'type': 'message',
            'data': json.dumps({
                "status": "SUCCESS",
                "chunks": 42,
                "filename": "protocol.pdf",
                "channel_id": 12345
            }).encode('utf-8')
        }

    mock_pubsub.listen.side_effect = mock_listen

    # Mock Redis connection from settings
    sys.modules['redis.asyncio'] = MagicMock()
    sys.modules['redis.asyncio'].Redis.from_url.return_value = mock_redis

    # 2. Mock Bot and Channel
    mock_bot = MagicMock()
    mock_channel = AsyncMock()
    mock_bot.get_channel.return_value = mock_channel
    mock_bot.wait_until_ready = AsyncMock()

    # 3. Instantiate Cog
    # We need to ensure imports work (e.g. settings)
    mock_settings = MagicMock()
    mock_settings.redis_url = "redis://localhost"
    sys.modules['bot.core.config'] = MagicMock()
    sys.modules['bot.core.config'].settings = mock_settings

    # Mock knowledge dependencies
    sys.modules['bot.core.knowledge.vector_db'] = MagicMock()
    sys.modules['bot.core.knowledge.ingest'] = MagicMock()

    from bot.cogs.knowledge import KnowledgeCog

    cog = KnowledgeCog(mock_bot)

    # 4. Trigger Event Handler Manually (to test logic)
    print("Triggering Event Handler...")
    test_data = {
        "status": "SUCCESS",
        "chunks": 10,
        "filename": "test.pdf",
        "channel_id": 999
    }
    await cog.handle_ingestion_event(test_data)

    # Check if channel.send was called
    mock_bot.get_channel.assert_called_with(999)
    if mock_channel.send.called:
        print("✅ Message sent to channel.")
        args = mock_channel.send.call_args[0][0]
        if "SHIELD OPERATOR REPORT" in args and "INTEGRITY_VERIFIED" in args:
             print("✅ Message content matches Shield Persona.")
        else:
             print(f"❌ Message content mismatch: {args}")
             return False
    else:
        print("❌ Message NOT sent.")
        return False

    print("\n--- 🚀 Feedback Loop Verified! ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_feedback_loop())
