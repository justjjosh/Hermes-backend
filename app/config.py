from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    postgres_password: str
    gemini_api_key: str
    mailgun_api_key: str
    mailgun_domain: str
    mailgun_webhook_signing_key: str
    api_base_url: str
    ai_provider: str
    secret_key: str

    class Config:
        env_file = ".env"

settings = Settings()
