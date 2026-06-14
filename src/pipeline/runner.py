import logging
import time

from sqlalchemy.orm import Session

from src.ai.name_extractor import extract_names
from src.ai.summarizer import summarize_article
from src.crm.webhook import notify_crm
from src.database import crud
from src.scraper import get_all_scrapers, load_scraper_config

logger = logging.getLogger(__name__)


def _save_people(db: Session, article_id: int, people: list[dict]) -> int:
    added = 0
    for person in people:
        crud.create_person(
            db,
            article_id=article_id,
            full_name=person["full_name"],
            role_context=person.get("role_context", ""),
            mention_count=person.get("mention_count", 1),
        )
        added += 1
    return added


def run_pipeline(db: Session) -> dict:
    """Run the full scrape → extract → summarize → store pipeline."""
    scrapers = get_all_scrapers()
    scraper_config = load_scraper_config()
    max_articles = scraper_config.get("max_articles_per_source", 20)

    totals = {
        "sources": 0,
        "found": 0,
        "new": 0,
        "people": 0,
        "people_updated": 0,
        "errors": [],
    }

    for index, scraper in enumerate(scrapers):
        if index > 0:
            time.sleep(10)
        totals["sources"] += 1
        log = crud.create_scrape_log(db, scraper.name)
        found = 0
        new = 0

        try:
            articles = scraper.scrape()[:max_articles]
            found = len(articles)

            if found == 0:
                totals["errors"].append({
                    "source": scraper.name,
                    "error": "No articles returned (RSS may be rate-limited or unavailable)",
                })

            for article in articles:
                existing = crud.get_article_by_url(db, article.url)
                content = article.content or article.title
                author = article.author or ""
                people = extract_names(
                    article.title, content, author=author, url=article.url
                )

                if existing:
                    if people:
                        added = _save_people(db, existing.id, people)
                        totals["people"] += added
                        totals["people_updated"] += 1
                    continue

                summary = summarize_article(article.title, content)

                db_article = crud.create_article(
                    db,
                    source_name=article.source_name,
                    title=article.title,
                    url=article.url,
                    original_content=content,
                    summary=summary,
                    published_at=article.published_at,
                    region=article.region,
                )

                totals["people"] += _save_people(db, db_article.id, people)
                new += 1
                notify_crm("article.created", db_article.to_dict())

            crud.finish_scrape_log(db, log, articles_found=found, articles_new=new)
            db.commit()

        except Exception as e:
            logger.error("Scrape failed for %s: %s", scraper.name, e)
            crud.finish_scrape_log(
                db, log, articles_found=found, articles_new=new,
                status="failed", error_message=str(e),
            )
            db.commit()
            totals["errors"].append({"source": scraper.name, "error": str(e)})

        totals["found"] += found
        totals["new"] += new
        logger.info("Source %s: found=%d, new=%d", scraper.name, found, new)

    return totals
