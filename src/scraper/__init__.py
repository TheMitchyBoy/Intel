import logging
from pathlib import Path

import yaml

from src.config import settings
from src.scraper.base import BaseScraper
from src.scraper.generic import create_scraper

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "newspapers.yaml"


def load_sources() -> list[dict]:
    if not CONFIG_PATH.exists():
        logger.warning("Config file not found: %s", CONFIG_PATH)
        return []

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    sources = config.get("sources", [])
    return [s for s in sources if s.get("enabled", True)]


def load_scraper_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    return config.get("scraper", {})


def get_all_scrapers() -> list[BaseScraper]:
    sources = load_sources()
    return [create_scraper(source, settings.user_agent) for source in sources]
