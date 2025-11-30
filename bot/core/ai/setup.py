from langchain_openai import ChatOpenAI
from bot.core.config import settings
import os

def get_llm():
    # Ensure API key is set in environment if not already
    # Although pydantic settings usually load into env vars if defined there,
    # ChatOpenAI looks for OPENAI_API_KEY env var by default.
    # We will assume it's in the environment or passed via settings.
    # If using settings.OPENAI_API_KEY, we should pass it.

    # Check if OPENAI_API_KEY is in settings, if so, use it.
    # The memory said settings are in `bot/core/config.py`.
    # Let's inspect `bot/core/config.py` again to see if it has OPENAI_API_KEY.
    # Wait, I previously read `bot/core/config.py` and it DID NOT have OPENAI_API_KEY in the class definition.
    # But the memory said: "OpenAI settings (OPENAI_API_KEY, OPENAI_MODEL_NAME) are added to bot/core/config.py".
    # This implies I might need to update config.py or just rely on os.environ if the user set it there.
    # I'll try to get it from settings or os.environ.

    api_key = os.environ.get("OPENAI_API_KEY")
    model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-4-turbo-preview")

    return ChatOpenAI(api_key=api_key, model=model_name, temperature=0)
