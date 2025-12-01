from langchain_openai import ChatOpenAI
from bot.core.config import settings
import os

def get_llm():
    # Check if OPENAI_API_KEY is in settings, if so, use it.
    # Otherwise fallback to os.environ which ChatOpenAI checks by default.
    api_key = settings.OPENAI_API_KEY
    if not api_key or api_key.startswith("sk-dummy"):
         api_key = os.environ.get("OPENAI_API_KEY")

    model_name = settings.OPENAI_MODEL_NAME or os.environ.get("OPENAI_MODEL_NAME", "gpt-4-turbo-preview")

    return ChatOpenAI(api_key=api_key, model=model_name, temperature=0)
