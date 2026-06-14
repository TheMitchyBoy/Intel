import os

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.database.url import (
    LOCAL_DATABASE_URL,
    database_diagnostics,
    database_setup_error,
    resolve_database_url,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default=LOCAL_DATABASE_URL,
        validation_alias=AliasChoices(
            "DATABASE_PRIVATE_URL",
            "DATABASE_URL",
            "POSTGRES_PRIVATE_URL",
            "POSTGRES_URL",
            "database_url",
        ),
    )
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "dev-api-key"
    scrape_interval_hours: int = 24
    scrape_schedule_enabled: bool = True
    scrape_schedule_hour: int = 6
    scrape_schedule_minute: int = 0
    scrape_timezone: str = "America/Sitka"
    user_agent: str = "IntelBot/1.0 (Newspaper Intelligence Scraper)"
    crm_webhook_url: str = ""
    crm_webhook_secret: str = ""
    port: int = 8000

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, value: str | None) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return ""
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    def is_railway(self) -> bool:
        return bool(os.environ.get("RAILWAY_ENVIRONMENT"))

    def resolved_database_url(self) -> str:
        return resolve_database_url(self.database_url)

    def database_is_configured(self) -> bool:
        return bool(self.resolved_database_url())

    def validate_database_config(self) -> None:
        if not self.database_is_configured():
            raise RuntimeError(database_setup_error())
        url = self.resolved_database_url()
        if ("localhost" in url or "127.0.0.1" in url) and self.is_railway():
            raise RuntimeError(
                "DATABASE_URL points to localhost on Railway.\n"
                "Use Postgres → Connect → Intel, or Add Reference → DATABASE_URL"
            )

    def database_diagnostics(self) -> dict:
        return database_diagnostics()


settings = Settings()
