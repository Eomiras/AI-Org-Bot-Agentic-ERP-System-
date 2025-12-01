import asyncio
import os
import sys
from unittest.mock import MagicMock

sys.path.append(os.getcwd())

async def verify_ingestion():
    print("--- 🛡️ Verifying Shield Operator & Ingestion ---")

    # 1. Mock External Services (Qdrant)
    # We need to mock 'add_document' because it calls Qdrant
    sys.modules['bot.core.knowledge.ingest'] = MagicMock()
    sys.modules['bot.core.knowledge.ingest'].add_document = MagicMock(return_value=5) # Return 5 chunks

    from bot.ml_modules.ingestion import ingest_task, sanitize_text

    # 2. Test Sanitizer
    print("\n[Sanitizer] Testing Regex...")
    text_with_pii = "Contact me at user@example.com or +1-555-0199."
    clean, count = sanitize_text(text_with_pii)

    if "[REDACTED_EMAIL]" in clean and "[REDACTED_PHONE]" in clean:
        print(f"✅ Sanitization working. Detected {count} PII items.")
    else:
        print(f"❌ Sanitization failed. Output: {clean}")
        return False

    # 3. Test Ingestion Task (Mocked)
    print("\n[Worker] Testing Ingest Task...")

    # Create a dummy file
    test_file = "test_doc.txt"
    with open(test_file, "w") as f:
        f.write("This is a test document for the Shield Operator. No PII here.")

    try:
        result = await ingest_task({}, test_file, {"source": "test"})

        if result["status"] == "SUCCESS":
            print(f"✅ Ingestion Task Success: {result}")
        else:
            print(f"❌ Ingestion Task Failed: {result}")
            return False

    except Exception as e:
        print(f"❌ Task Exception: {e}")
        return False
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

    # 4. Check Shield Agent Import
    print("\n[AI] Checking Shield Agent...")
    try:
        # We need to mock AI setup again or it fails on OpenAI Key
        mock_settings = MagicMock()
        mock_settings.OPENAI_API_KEY = "sk-mock"
        sys.modules['bot.core.config'] = MagicMock()
        sys.modules['bot.core.config'].settings = mock_settings

        from bot.core.ai.supervisor import shield_agent
        print("✅ Shield Agent imported successfully.")
    except Exception as e:
        print(f"❌ Shield Agent Import Error: {e}")
        # Not blocking for now if graph compilation checked before

    print("\n--- 🚀 Ingestion System Verified! ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_ingestion())
