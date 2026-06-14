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

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (compatible; IntelBot/1.0; +https://github.com/TheMitchyBoy/Intel) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

BLOX_CONTENT_SELECTORS = (
    "#article-body, [itemprop='articleBody'], .asset-body, "
    ".subscriber-preview, .asset-content p"
)


BROWSER_HEADERS = {
    "User-Agent": BROWSER_USER_AGENT,
    "Accept": "application/rss+xml, application/xml, text/xml, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.ketchikandailynews.com/",
}


class RSSScraper(BaseScraper):
    """Scrape articles from an RSS/Atom feed."""

    def _fetch_feed(self, url: str):
        for attempt in range(3):
            try:
                with httpx.Client(timeout=30, headers=BROWSER_HEADERS, follow_redirects=True) as client:
                    response = client.get(url)
                    if response.status_code == 429:
                        wait = 2 ** attempt
                        logger.warning("RSS rate limited for %s, retrying in %ds", url, wait)
                        time.sleep(wait)
                        continue
                    response.raise_for_status()
                    return feedparser.parse(response.text)
            except Exception as e:
                if attempt == 2:
                    logger.warning("RSS httpx fetch failed for %s: %s — trying feedparser fallback", url, e)
                    return feedparser.parse(url, agent=BROWSER_USER_AGENT)
                time.sleep(2 ** attempt)
        return feedparser.parse(url, agent=BROWSER_USER_AGENT)

    def scrape(self) -> list[ScrapedArticle]:
        url = self.config["url"]
        logger.info("Fetching RSS feed: %s", url)

        feed = self._fetch_feed(url)

        if feed.bozo and not feed.entries:
            logger.warning(
                "RSS feed failed for %s: %s (got HTML or rate-limited?)",
                self.name,
                getattr(feed, "bozo_exception", "unknown"),
            )
            return []

        articles: list[ScrapedArticle] = []

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue
            if not self._passes_url_filters(link):
                continue

            published_at = None
            if entry.get("published"):
                try:
                    published_at = parsedate_to_datetime(entry.published)
                except (ValueError, TypeError):
                    pass

            content = self._extract_content(entry, link)
            author = ""
            if entry.get("author"):
                author = str(entry.author).strip()
            elif getattr(entry, "author_detail", None):
                author = (entry.author_detail.get("name") or "").strip()

            articles.append(
                ScrapedArticle(
                    title=title,
                    url=link,
                    content=content,
                    published_at=published_at,
                    source_name=self.name,
                    region=self.region,
                    author=author,
                )
            )

        logger.info("Found %d articles from RSS: %s", len(articles), self.name)
        return articles

    def _passes_url_filters(self, link: str) -> bool:
        filters = self.config.get("filters", {})
        must_contain = filters.get("url_must_contain")
        must_not_contain = filters.get("url_must_not_contain")

        if must_contain and must_contain not in link:
            return False
        if must_not_contain and must_not_contain in link:
            return False
        return True

    def _extract_content(self, entry, link: str) -> str:
        parts: list[str] = []

        if entry.get("author"):
            parts.append(str(entry.author))
        if getattr(entry, "author_detail", None) and entry.author_detail.get("name"):
            parts.append(entry.author_detail.name)

        if entry.get("content"):
            parts.append(
                BeautifulSoup(entry.content[0].value, "lxml").get_text(separator=" ", strip=True)
            )
        elif entry.get("summary"):
            parts.append(BeautifulSoup(entry.summary, "lxml").get_text(separator=" ", strip=True))

        rss_text = " ".join(parts).strip()

        # Always try to fetch the full article — RSS summaries are too short for name extraction
        page_text = self._fetch_page_content(link)
        if len(page_text) > len(rss_text):
            return f"{rss_text} {page_text}".strip() if rss_text else page_text
        return rss_text or page_text

    def _content_selector(self) -> str:
        selectors = self.config.get("selectors", {})
        return selectors.get("content", BLOX_CONTENT_SELECTORS)

    def _fetch_page_content(self, url: str) -> str:
        delay = self.config.get("request_delay_seconds", 0)
        if delay:
            time.sleep(delay)
        try:
            with httpx.Client(timeout=30, headers=BROWSER_HEADERS, follow_redirects=True) as client:
                response = client.get(url)
                if response.status_code == 429:
                    logger.warning("Rate limited fetching %s", url)
                    return ""
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()

                content_el = soup.select_one(self._content_selector())
                if content_el:
                    return content_el.get_text(separator=" ", strip=True)

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
