from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    postgres_password: str
    gemini_api_key: str
    resend_api_key: str
    api_base_url: str = "http://localhost:8000"
    ai_provider: str
    secret_key: str

    class Config:
        env_file = ".env"

settings = Settings()
