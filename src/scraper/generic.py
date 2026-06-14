import logging
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup

from src.scraper.base import BaseScraper, ScrapedArticle

logger = logging.getLogger(__name__)


class RSSScraper(BaseScraper):
    """Scrape articles from an RSS/Atom feed."""

    def scrape(self) -> list[ScrapedArticle]:
        url = self.config["url"]
        logger.info("Fetching RSS feed: %s", url)

        feed = feedparser.parse(url, agent=self.user_agent)
        articles: list[ScrapedArticle] = []

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            published_at = None
            if entry.get("published"):
                try:
                    published_at = parsedate_to_datetime(entry.published)
                except (ValueError, TypeError):
                    pass

            content = self._extract_content(entry, link)
            articles.append(
                ScrapedArticle(
                    title=title,
                    url=link,
                    content=content,
                    published_at=published_at,
                    source_name=self.name,
                    region=self.region,
                )
            )

        logger.info("Found %d articles from RSS: %s", len(articles), self.name)
        return articles

    def _extract_content(self, entry, link: str) -> str:
        if entry.get("content"):
            return BeautifulSoup(entry.content[0].value, "lxml").get_text(separator=" ", strip=True)
        if entry.get("summary"):
            return BeautifulSoup(entry.summary, "lxml").get_text(separator=" ", strip=True)
        return self._fetch_page_content(link)

    def _fetch_page_content(self, url: str) -> str:
        try:
            with httpx.Client(timeout=30, headers={"User-Agent": self.user_agent}) as client:
                response = client.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                paragraphs = soup.find_all("p")
                return " ".join(p.get_text(strip=True) for p in paragraphs[:20])
        except Exception as e:
            logger.warning("Failed to fetch full content from %s: %s", url, e)
            return ""


class HTMLScraper(BaseScraper):
    """Scrape articles from an HTML news page using CSS selectors."""

    def scrape(self) -> list[ScrapedArticle]:
        url = self.config["url"]
        selectors = self.config.get("selectors", {})
        logger.info("Scraping HTML page: %s", url)

        with httpx.Client(timeout=30, headers={"User-Agent": self.user_agent}) as client:
            response = client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        article_selector = selectors.get("article_list", "article")
        articles: list[ScrapedArticle] = []

        for element in soup.select(article_selector):
            title_el = element.select_one(selectors.get("title", "h2"))
            link_el = element.select_one(selectors.get("link", "a"))
            if not title_el or not link_el:
                continue

            title = title_el.get_text(strip=True)
            link = urljoin(url, link_el.get("href", ""))
            content = self._fetch_article_content(link, selectors)

            articles.append(
                ScrapedArticle(
                    title=title,
                    url=link,
                    content=content,
                    published_at=datetime.utcnow(),
                    source_name=self.name,
                    region=self.region,
                )
            )

        logger.info("Found %d articles from HTML: %s", len(articles), self.name)
        return articles

    def _fetch_article_content(self, url: str, selectors: dict) -> str:
        content_selector = selectors.get("content", "div.article-body, article p")
        try:
            with httpx.Client(timeout=30, headers={"User-Agent": self.user_agent}) as client:
                response = client.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                content_el = soup.select_one(content_selector)
                if content_el:
                    return content_el.get_text(separator=" ", strip=True)
                paragraphs = soup.find_all("p")
                return " ".join(p.get_text(strip=True) for p in paragraphs[:20])
        except Exception as e:
            logger.warning("Failed to fetch article %s: %s", url, e)
            return ""


def create_scraper(source_config: dict, user_agent: str) -> BaseScraper:
    scraper_type = source_config.get("type", "rss")
    if scraper_type == "html":
        return HTMLScraper(source_config, user_agent)
    return RSSScraper(source_config, user_agent)
