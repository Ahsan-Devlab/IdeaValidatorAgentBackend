from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    openrouter_api_key: str
    groq_api_key: str
    tavily_api_key: str

    class Config:
        env_file = ".env"

    supabase_url: str = ""
    supabase_secret_key: str = ""
    # Frontend addresses allowed to call this API, separated by commas
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

settings = Settings()