from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.database import contacts
from src.database.models import Article, Person, PipelineRun, ScrapeLog


def get_article_by_url(db: Session, url: str) -> Article | None:
    return db.query(Article).filter(Article.url == url).first()


def create_article(db: Session, **kwargs) -> Article:
    article = Article(**kwargs)
    db.add(article)
    db.flush()
    return article


def create_person(db: Session, article_id: int, full_name: str, role_context: str = "", mention_count: int = 1):
    """Legacy wrapper — saves to Contact + PersonMention."""
    return contacts.save_mention(
        db,
        article_id,
        {
            "full_name": full_name,
            "role_context": role_context,
            "mention_count": mention_count,
            "sources": ["legacy"],
            "confidence": 0.7,
        },
    )


def get_articles(
    db: Session,
    *,
    source: str | None = None,
    region: str | None = None,
    since: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Article]:
    query = db.query(Article)
    if source:
        query = query.filter(Article.source_name == source)
    if region:
        query = query.filter(Article.region == region)
    if since:
        query = query.filter(Article.scraped_at >= since)
    return query.order_by(Article.scraped_at.desc()).offset(offset).limit(limit).all()


def get_people_grouped(db: Session, **kwargs) -> list[dict]:
    return contacts.get_contacts(db, **kwargs)


def get_person_grouped(db: Session, contact_id: int) -> dict | None:
    return contacts.get_contact_by_id(db, contact_id)


def cleanup_invalid_people(db: Session) -> int:
    return contacts.cleanup_invalid_contacts(db)


def get_person_by_id(db: Session, person_id: int) -> Person | None:
    return db.query(Person).filter(Person.id == person_id).first()


def get_article_by_id(db: Session, article_id: int) -> Article | None:
    return db.query(Article).filter(Article.id == article_id).first()


def get_stats(db: Session) -> dict:
    return contacts.get_stats_contacts(db)


def create_scrape_log(db: Session, source_name: str) -> ScrapeLog:
    log = ScrapeLog(source_name=source_name)
    db.add(log)
    db.flush()
    return log


def finish_scrape_log(
    db: Session,
    log: ScrapeLog,
    *,
    articles_found: int,
    articles_new: int,
    status: str = "completed",
    error_message: str | None = None,
) -> None:
    log.finished_at = datetime.utcnow()
    log.articles_found = articles_found
    log.articles_new = articles_new
    log.status = status
    log.error_message = error_message


def create_pipeline_run(db: Session) -> PipelineRun | None:
    """Create a new pipeline run, or return None if one is already running."""
    stale_cutoff = datetime.utcnow() - timedelta(minutes=30)
    running = (
        db.query(PipelineRun)
        .filter(PipelineRun.status == "running")
        .order_by(PipelineRun.started_at.desc())
        .first()
    )
    if running:
        if running.started_at >= stale_cutoff:
            return None
        running.status = "failed"
        running.error_message = "Timed out after 30 minutes"
        running.finished_at = datetime.utcnow()

    run = PipelineRun(status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finish_pipeline_run(
    db: Session,
    run_id: int,
    *,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    import json

    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        return
    run.finished_at = datetime.utcnow()
    if error:
        run.status = "failed"
        run.error_message = error
    else:
        run.status = "completed"
        run.result_json = json.dumps(result or {})
    db.commit()


def get_pipeline_run(db: Session, run_id: int) -> PipelineRun | None:
    return db.query(PipelineRun).filter(PipelineRun.id == run_id).first()


def get_latest_pipeline_run(db: Session) -> PipelineRun | None:
    return db.query(PipelineRun).order_by(PipelineRun.id.desc()).first()
