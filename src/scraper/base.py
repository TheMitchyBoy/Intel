from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScrapedArticle:
    title: str
    url: str
    content: str
    published_at: datetime | None = None
    source_name: str = ""
    region: str = ""
    author: str = ""


class BaseScraper(ABC):
    """Base class for newspaper scrapers."""

    def __init__(self, source_config: dict, user_agent: str):
        self.config = source_config
        self.user_agent = user_agent
        self.name = source_config.get("name", "Unknown")
        self.region = source_config.get("region", "")

    @abstractmethod
    def scrape(self) -> list[ScrapedArticle]:
        pass
