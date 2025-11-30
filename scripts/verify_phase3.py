import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

async def verify_phase3():
    print("--- 🧠 Verifying Phase 3: The Hive Mind ---")

    # 1. Verify Imports for AI Module
    print("\n[AI Architect] Checking Supervisor Graph...")
    try:
        from bot.core.ai.supervisor import app
        print("✅ Successfully imported Supervisor Graph 'app'.")
    except ImportError as e:
        print(f"❌ Failed to import Supervisor: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing Supervisor: {e}")
        return False

    # 2. Verify Imports for Knowledge Module
    print("\n[Librarian] Checking Knowledge Base...")
    try:
        from bot.core.knowledge.vector_db import get_retriever, get_embeddings
        print("✅ Successfully imported Knowledge Module.")

        # Test imports of heavy libraries without actually instantiating (slow)
        import qdrant_client
        import langchain
        import sentence_transformers
        print("✅ Key RAG dependencies are installed.")

    except ImportError as e:
        print(f"❌ Failed to import Knowledge dependencies: {e}")
        return False
    except Exception as e:
        print(f"❌ Error in Knowledge module verification: {e}")
        return False

    # 3. Verify Cog Loading
    print("\n[Cogs] Checking New Cogs...")
    try:
        __import__("bot.cogs.ai_chat", fromlist=[''])
        print("✅ Imported bot.cogs.ai_chat")

        __import__("bot.cogs.knowledge", fromlist=[''])
        print("✅ Imported bot.cogs.knowledge")
    except Exception as e:
        print(f"❌ Failed to import Cogs: {e}")
        return False

    print("\n--- 🚀 Phase 3 Verification Complete! ---")
    return True

if __name__ == "__main__":
    asyncio.run(verify_phase3())
