from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.ai.person_names import is_valid_person_name, normalize_person_name, person_name_key
from src.database.models import Article, Person, PipelineRun, ScrapeLog


def get_article_by_url(db: Session, url: str) -> Article | None:
    return db.query(Article).filter(Article.url == url).first()


def create_article(db: Session, **kwargs) -> Article:
    article = Article(**kwargs)
    db.add(article)
    db.flush()
    return article


def create_person(db: Session, article_id: int, full_name: str, role_context: str = "", mention_count: int = 1) -> Person | None:
    full_name = normalize_person_name(full_name)
    if not is_valid_person_name(full_name, allow_single_word=role_context == "Obituary"):
        return None

    key = person_name_key(full_name)
    for existing in db.query(Person).filter(Person.article_id == article_id).all():
        if person_name_key(existing.full_name) == key:
            existing.mention_count = mention_count
            existing.role_context = role_context or existing.role_context
            if existing.full_name != full_name and full_name.istitle():
                existing.full_name = full_name
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
    query = db.query(Person).join(Article, Person.article_id == Article.id)
    if name:
        query = query.filter(Person.full_name.ilike(f"%{name}%"))
    if since:
        query = query.filter(Article.scraped_at >= since)
    return query.order_by(Article.scraped_at.desc()).offset(offset).limit(limit).all()


def _person_group_dict(person: Person) -> dict:
    article = person.article
    return {
        "mention_id": person.id,
        "article_id": person.article_id,
        "title": article.title if article else None,
        "url": article.url if article else None,
        "summary": article.summary if article else None,
        "scraped_at": article.scraped_at.isoformat() if article and article.scraped_at else None,
        "mention_count": person.mention_count,
        "role_context": person.role_context,
    }


def get_people_grouped(
    db: Session,
    *,
    name: str | None = None,
    since: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Return unique people with all linked articles merged."""
    query = (
        db.query(Person)
        .join(Article, Person.article_id == Article.id)
        .order_by(Article.scraped_at.desc())
    )
    if name:
        query = query.filter(Person.full_name.ilike(f"%{name}%"))
    if since:
        query = query.filter(Article.scraped_at >= since)

    groups: dict[str, dict] = {}
    for person in query.all():
        if not is_valid_person_name(
            person.full_name,
            allow_single_word=person.role_context == "Obituary",
        ):
            continue

        key = person_name_key(person.full_name)
        article_ref = _person_group_dict(person)

        if key not in groups:
            groups[key] = {
                "id": person.id,
                "full_name": normalize_person_name(person.full_name),
                "role_context": person.role_context,
                "mention_count": 0,
                "article_count": 0,
                "latest_seen": article_ref["scraped_at"],
                "articles": [],
                "_article_ids": set(),
            }

        group = groups[key]
        if person.id < group["id"]:
            group["id"] = person.id
        if normalize_person_name(person.full_name).istitle():
            group["full_name"] = normalize_person_name(person.full_name)
        group["mention_count"] += person.mention_count
        if person.role_context and not group["role_context"]:
            group["role_context"] = person.role_context

        if person.article_id not in group["_article_ids"]:
            group["_article_ids"].add(person.article_id)
            group["articles"].append(article_ref)
            group["article_count"] += 1
            scraped = article_ref["scraped_at"]
            if scraped and (not group["latest_seen"] or scraped > group["latest_seen"]):
                group["latest_seen"] = scraped

    results = sorted(
        groups.values(),
        key=lambda g: (g["latest_seen"] or "", g["full_name"]),
        reverse=True,
    )

    for group in results:
        group.pop("_article_ids", None)
        latest = group["articles"][0] if group["articles"] else {}
        group["article_id"] = latest.get("article_id")
        group["article_title"] = latest.get("title")
        group["article_url"] = latest.get("url")
        group["article_summary"] = latest.get("summary")
        group["created_at"] = group["latest_seen"]

    return results[offset : offset + limit]


def get_person_grouped(db: Session, person_id: int) -> dict | None:
    person = get_person_by_id(db, person_id)
    if not person:
        return None

    key = person_name_key(person.full_name)
    matches = [
        p
        for p in db.query(Person).join(Article, Person.article_id == Article.id).order_by(Article.scraped_at.desc()).all()
        if person_name_key(p.full_name) == key
        and is_valid_person_name(p.full_name, allow_single_word=p.role_context == "Obituary")
    ]
    if not matches:
        return None

    group: dict = {
        "id": min(p.id for p in matches),
        "full_name": normalize_person_name(matches[0].full_name),
        "role_context": next((p.role_context for p in matches if p.role_context), None),
        "mention_count": sum(p.mention_count for p in matches),
        "article_count": 0,
        "latest_seen": None,
        "articles": [],
    }
    seen_articles: set[int] = set()
    for p in matches:
        if p.article_id in seen_articles:
            continue
        seen_articles.add(p.article_id)
        ref = _person_group_dict(p)
        group["articles"].append(ref)
        group["article_count"] += 1
        if not group["latest_seen"]:
            group["latest_seen"] = ref["scraped_at"]

    latest = group["articles"][0] if group["articles"] else {}
    group["article_id"] = latest.get("article_id")
    group["article_title"] = latest.get("title")
    group["article_url"] = latest.get("url")
    group["article_summary"] = latest.get("summary")
    group["created_at"] = group["latest_seen"]
    return group


def cleanup_invalid_people(db: Session) -> int:
    """Remove person records that are places, organizations, or junk names."""
    removed = 0
    for person in db.query(Person).all():
        if not is_valid_person_name(
            person.full_name,
            allow_single_word=person.role_context == "Obituary",
        ):
            db.delete(person)
            removed += 1
    if removed:
        db.commit()
    return removed


def count_unique_people(db: Session, *, since: datetime | None = None) -> int:
    query = db.query(Person).join(Article, Person.article_id == Article.id)
    if since:
        query = query.filter(Article.scraped_at >= since)
    keys = {
        person_name_key(p.full_name)
        for p in query.all()
        if is_valid_person_name(p.full_name, allow_single_word=p.role_context == "Obituary")
    }
    return len(keys)


def get_person_by_id(db: Session, person_id: int) -> Person | None:
    return db.query(Person).filter(Person.id == person_id).first()


def get_article_by_id(db: Session, article_id: int) -> Article | None:
    return db.query(Article).filter(Article.id == article_id).first()


def get_stats(db: Session) -> dict:
    total_articles = db.query(Article).count()
    total_people = count_unique_people(db)
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_articles = db.query(Article).filter(Article.scraped_at >= last_24h).count()
    recent_people = count_unique_people(db, since=last_24h)
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
