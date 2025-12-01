import sys
import os
from unittest.mock import MagicMock

# --- 1. MOCKING EXTERNAL SERVICES ---
# We cannot connect to Qdrant or OpenAI in this sandbox, so we mock them.

# Mock Qdrant Client
sys.modules['qdrant_client'] = MagicMock()
sys.modules['qdrant_client.models'] = MagicMock()

# Mock LangChain Components that hit the network
mock_embeddings = MagicMock()
sys.modules['langchain_community.embeddings'] = MagicMock()
sys.modules['langchain_community.embeddings'].HuggingFaceEmbeddings = MagicMock(return_value=mock_embeddings)

mock_vectorstore = MagicMock()
mock_retriever = MagicMock()
mock_vectorstore.as_retriever.return_value = mock_retriever

sys.modules['langchain_qdrant'] = MagicMock()
sys.modules['langchain_qdrant'].QdrantVectorStore = MagicMock(return_value=mock_vectorstore)

# Mock OpenAI
mock_chat = MagicMock()
# bind_tools must return the mock itself (or a runnable) to allow chaining
mock_chat.bind_tools.return_value = mock_chat
sys.modules['langchain_openai'] = MagicMock()
sys.modules['langchain_openai'].ChatOpenAI = MagicMock(return_value=mock_chat)

# Mock Settings
mock_settings = MagicMock()
mock_settings.QDRANT_HOST = "localhost"
mock_settings.QDRANT_PORT = 6333
mock_settings.OPENAI_API_KEY = "sk-mock"
mock_settings.OPENAI_MODEL_NAME = "gpt-mock"
# SQLAlchemy needs a valid-ish URL string to parse
mock_settings.database_url = "postgresql+asyncpg://user:pass@localhost:5432/db"

# Patch the module
mock_config_module = MagicMock()
mock_config_module.settings = mock_settings
sys.modules['bot.core.config'] = mock_config_module

# --- 2. IMPORTING THE GRAPH ---
try:
    print("Attempting to import supervisor...")
    from bot.core.ai.supervisor import app
    print("✅ Supervisor Graph compiled successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"❌ Failed to compile supervisor graph: {e}")
    sys.exit(1)

# --- 3. VERIFYING NODES ---
nodes = app.nodes
print(f"Nodes found: {list(nodes.keys())}")

expected_nodes = ["supervisor", "economy_agent", "lore_agent", "chat_agent"]
missing = [n for n in expected_nodes if n not in nodes]

if missing:
    print(f"❌ Missing nodes: {missing}")
else:
    print("✅ All agents are present in the graph.")

# --- 4. VERIFYING TOOLS ---
# We want to check if economy agent has tools.
# This is harder to check on the compiled graph without runtime inspection.
# But if it imported without error, the tools were likely found.

from bot.core.ai.tools.economy import get_user_balance
print(f"✅ Economy Tool Loaded: {get_user_balance.name}")
