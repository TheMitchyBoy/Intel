import os

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql://intel:intel_secret@localhost:5432/intel_db",
        validation_alias=AliasChoices(
            "DATABASE_PRIVATE_URL",
            "DATABASE_URL",
            "POSTGRES_URL",
            "database_url",
        ),
    )
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

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    def is_railway(self) -> bool:
        return bool(os.environ.get("RAILWAY_ENVIRONMENT"))

    def validate_database_config(self) -> None:
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            if self.is_railway():
                raise RuntimeError(
                    "DATABASE_URL is not configured on Railway.\n"
                    "Fix: open your web service → Variables → + New Variable → "
                    "Add Reference → select your PostgreSQL service → DATABASE_URL"
                )


settings = Settings()
