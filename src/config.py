import os
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_URL = "postgresql://intel:intel_secret@localhost:5432/intel_db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default=LOCAL_DATABASE_URL,
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
    def fix_database_url(cls, value: str | None) -> str:
        # Railway sets DATABASE_URL to "" when ${{Postgres.DATABASE_URL}} has no Postgres service
        if value is None or (isinstance(value, str) and not value.strip()):
            return ""
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    def is_railway(self) -> bool:
        return bool(os.environ.get("RAILWAY_ENVIRONMENT"))

    def resolved_database_url(self) -> str:
        url = (self.database_url or "").strip()
        if url:
            return url
        if self.is_railway():
            return ""
        return LOCAL_DATABASE_URL

    def validate_database_config(self) -> None:
        url = self.resolved_database_url()
        if not url:
            raise RuntimeError(
                "DATABASE_URL is empty — the Postgres service reference could not be resolved.\n\n"
                "Fix (choose one):\n"
                "  1. Run: railway config apply   (provisions Postgres from .railway/railway.ts)\n"
                "  2. Dashboard: + New → Database → PostgreSQL, then link DATABASE_URL to Intel\n"
            )
        if ("localhost" in url or "127.0.0.1" in url) and self.is_railway():
            raise RuntimeError(
                "DATABASE_URL points to localhost on Railway.\n"
                "Link Postgres: Intel service → Variables → Add Reference → Postgres → DATABASE_URL"
            )


settings = Settings()
