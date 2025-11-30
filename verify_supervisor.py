
import sys
import os
from unittest.mock import MagicMock

# Mock modules that might rely on external services not available in sandbox (like Qdrant)
sys.modules['qdrant_client'] = MagicMock()
sys.modules['langchain_qdrant'] = MagicMock()

# Mock settings
mock_settings = MagicMock()
mock_settings.QDRANT_HOST = "localhost"
mock_settings.QDRANT_PORT = 6333
sys.modules['bot.core.config'] = MagicMock()
sys.modules['bot.core.config'].settings = mock_settings

# Mock Vector DB parts because they try to connect to Qdrant
# We need to mock 'bot.core.knowledge.vector_db' partially or fully
# But since we want to import it, we can mock the functions inside it
# However, importing 'bot.core.knowledge.vector_db' will trigger the top-level imports.
# We already mocked 'qdrant_client' and 'langchain_qdrant', so the imports should pass.

try:
    from bot.core.ai.supervisor import app
    print("Supervisor Graph compiled successfully.")
except Exception as e:
    print(f"Failed to compile supervisor graph: {e}")
    sys.exit(1)

# Basic verification that the nodes exist
assert "supervisor" in app.nodes
assert "lore_agent" in app.nodes
assert "chat_agent" in app.nodes
print("Nodes verified.")
