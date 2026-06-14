"""Re-run name extraction on all stored articles."""

import logging

from sqlalchemy.orm import Session

from src.ai.name_extractor import extract_names
from src.database import contacts
from src.database.models import Article

logger = logging.getLogger(__name__)


def reprocess_all_names(db: Session) -> dict:
    articles = db.query(Article).order_by(Article.scraped_at.desc()).all()
    totals = {
        "articles": len(articles),
        "mentions_created": 0,
        "mentions_removed": 0,
        "contacts_updated": 0,
    }

    for article in articles:
        totals["mentions_removed"] += contacts.delete_mentions_for_article(db, article.id)
        content = article.original_content or article.title
        people = extract_names(article.title, content, url=article.url)

        for person in people:
            if contacts.save_mention(db, article.id, person):
                totals["mentions_created"] += 1

    removed = contacts.cleanup_invalid_contacts(db)
    totals["invalid_contacts_removed"] = removed
    db.commit()
    logger.info("Reprocessed names: %s", totals)
    return totals
