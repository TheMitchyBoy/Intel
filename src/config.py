from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://intel:intel_secret@localhost:5432/intel_db"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "dev-api-key"
    scrape_interval_hours: int = 6
    user_agent: str = "IntelBot/1.0 (Newspaper Intelligence Scraper)"
    crm_webhook_url: str = ""
    crm_webhook_secret: str = ""
    port: int = 8000

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, value: str) -> str:
        # Railway and other hosts often provide postgres:// instead of postgresql://
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value


settings = Settings()
