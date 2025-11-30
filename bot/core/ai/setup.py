from langchain_openai import ChatOpenAI
from bot.core.config import settings

def get_llm():
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL_NAME,
        temperature=0
    )
