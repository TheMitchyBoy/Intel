from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.database.models import Article, Person, ScrapeLog


def get_article_by_url(db: Session, url: str) -> Article | None:
    return db.query(Article).filter(Article.url == url).first()


def create_article(db: Session, **kwargs) -> Article:
    article = Article(**kwargs)
    db.add(article)
    db.flush()
    return article


def create_person(db: Session, article_id: int, full_name: str, role_context: str = "", mention_count: int = 1) -> Person:
    existing = (
        db.query(Person)
        .filter(Person.article_id == article_id, Person.full_name == full_name)
        .first()
    )
    if existing:
        existing.mention_count = mention_count
        existing.role_context = role_context or existing.role_context
        return existing

    person = Person(
        article_id=article_id,
        full_name=full_name,
        role_context=role_context,
        mention_count=mention_count,
    )
    db.add(person)
    return person


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


def get_people(
    db: Session,
    *,
    name: str | None = None,
    since: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Person]:
    query = db.query(Person)
    if name:
        query = query.filter(Person.full_name.ilike(f"%{name}%"))
    if since:
        query = query.filter(Person.created_at >= since)
    return query.order_by(Person.created_at.desc()).offset(offset).limit(limit).all()


def get_person_by_id(db: Session, person_id: int) -> Person | None:
    return db.query(Person).filter(Person.id == person_id).first()


def get_article_by_id(db: Session, article_id: int) -> Article | None:
    return db.query(Article).filter(Article.id == article_id).first()


def get_stats(db: Session) -> dict:
    total_articles = db.query(Article).count()
    total_people = db.query(Person).count()
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_articles = db.query(Article).filter(Article.scraped_at >= last_24h).count()
    recent_people = db.query(Person).filter(Person.created_at >= last_24h).count()
    return {
        "total_articles": total_articles,
        "total_people": total_people,
        "articles_last_24h": recent_articles,
        "people_last_24h": recent_people,
    }


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
