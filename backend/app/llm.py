from langchain_openai import ChatOpenAI
from app.config import settings

def build_llm(temperature: float = 0.2):
    main = ChatOpenAI(
        model_name="openrouter/free",
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
        temperature=temperature,
        max_retries=1,
    ) 


    backup = ChatOpenAI(
        model = "openai/gpt-oss-20b",
        base_url="https://api.groq.com/openai/v1",
        api_key=settings.groq_api_key,
        temperature=temperature,
        max_retries=1,
        )

    return main.with_fallbacks([backup])
