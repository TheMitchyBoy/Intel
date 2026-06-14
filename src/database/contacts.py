"""Contact and mention persistence with fuzzy deduplication."""

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.ai.name_confidence import auto_review_status, compute_confidence
from src.ai.person_names import (
    is_valid_person_name,
    names_are_similar,
    normalize_person_name,
    person_name_key,
    pick_better_display_name,
)
from src.database.models import Article, Contact, Person, PersonMention

logger = logging.getLogger(__name__)


def find_contact(db: Session, full_name: str) -> Contact | None:
    """Find existing contact by exact or fuzzy name match."""
    full_name = normalize_person_name(full_name)
    key = person_name_key(full_name)

    exact = db.query(Contact).filter(Contact.name_key == key).first()
    if exact:
        return exact

    for contact in db.query(Contact).filter(Contact.review_status != "rejected").all():
        if names_are_similar(contact.full_name, full_name):
            return contact
    return None


def get_or_create_contact(db: Session, full_name: str, *, confidence: float, sources: list[str]) -> Contact:
    full_name = normalize_person_name(full_name)
    key = person_name_key(full_name)
    existing = find_contact(db, full_name)

    if existing:
        existing.full_name = pick_better_display_name(existing.full_name, full_name)
        existing.name_key = person_name_key(existing.full_name)
        existing.updated_at = datetime.utcnow()
        if existing.review_status == "pending" and auto_review_status(confidence, sources) == "confirmed":
            existing.review_status = "confirmed"
        return existing

    contact = Contact(
        full_name=full_name,
        name_key=key,
        review_status=auto_review_status(confidence, sources),
    )
    db.add(contact)
    db.flush()
    return contact


def save_mention(
    db: Session,
    article_id: int,
    person_data: dict,
) -> PersonMention | None:
    """Save or update a person mention linked to a canonical contact."""
    full_name = normalize_person_name(person_data["full_name"])
    role_context = person_data.get("role_context", "")
    allow_single = role_context == "Obituary"
    if not is_valid_person_name(full_name, allow_single_word=allow_single):
        return None

    sources = list(person_data.get("sources", []))
    confidence = float(person_data.get("confidence", compute_confidence(sources)))
    mention_count = int(person_data.get("mention_count", 1))

    contact = get_or_create_contact(db, full_name, confidence=confidence, sources=sources)

    existing = (
        db.query(PersonMention)
        .filter(PersonMention.contact_id == contact.id, PersonMention.article_id == article_id)
        .first()
    )
    if existing:
        existing.mention_count = max(existing.mention_count, mention_count)
        existing.role_context = role_context or existing.role_context
        existing.confidence = max(existing.confidence, confidence)
        merged_sources = list(set(existing.sources_list() + sources))
        existing.sources = json.dumps(merged_sources)
        return existing

    mention = PersonMention(
        contact_id=contact.id,
        article_id=article_id,
        role_context=role_context,
        mention_count=mention_count,
        confidence=confidence,
        sources=json.dumps(sources),
    )
    db.add(mention)
    return mention


def _mention_article_dict(mention: PersonMention) -> dict:
    article = mention.article
    return {
        "mention_id": mention.id,
        "article_id": mention.article_id,
        "title": article.title if article else None,
        "url": article.url if article else None,
        "summary": article.summary if article else None,
        "scraped_at": article.scraped_at.isoformat() if article and article.scraped_at else None,
        "mention_count": mention.mention_count,
        "role_context": mention.role_context,
        "confidence": mention.confidence,
        "sources": mention.sources_list(),
    }


def contact_to_dict(contact: Contact) -> dict:
    mentions = sorted(
        contact.mentions,
        key=lambda m: m.article.scraped_at if m.article and m.article.scraped_at else datetime.min,
        reverse=True,
    )
    articles = [_mention_article_dict(m) for m in mentions]
    total_mentions = sum(m.mention_count for m in mentions)
    confidences = [m.confidence for m in mentions]
    all_sources: list[str] = []
    for m in mentions:
        all_sources.extend(m.sources_list())
    latest = articles[0] if articles else {}

    return {
        "id": contact.id,
        "full_name": contact.full_name,
        "role_context": next((m.role_context for m in mentions if m.role_context), None),
        "mention_count": total_mentions,
        "article_count": len(articles),
        "confidence": round(max(confidences) if confidences else 0.5, 2),
        "sources": sorted(set(all_sources)),
        "review_status": contact.review_status,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "latest_seen": latest.get("scraped_at"),
        "article_id": latest.get("article_id"),
        "article_title": latest.get("title"),
        "article_url": latest.get("url"),
        "article_summary": latest.get("summary"),
        "articles": articles,
    }


def get_contacts(
    db: Session,
    *,
    name: str | None = None,
    since: datetime | None = None,
    review_status: str | None = None,
    min_confidence: float | None = None,
    include_rejected: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    query = db.query(Contact).join(PersonMention).join(Article)
    if name:
        query = query.filter(Contact.full_name.ilike(f"%{name}%"))
    if since:
        query = query.filter(Article.scraped_at >= since)
    if review_status:
        query = query.filter(Contact.review_status == review_status)
    elif not include_rejected:
        query = query.filter(Contact.review_status != "rejected")
    if min_confidence is not None:
        query = query.filter(PersonMention.confidence >= min_confidence)

    contact_ids = {
        row[0]
        for row in query.with_entities(Contact.id).distinct().all()
    }
    if not contact_ids:
        return []
    contacts = (
        db.query(Contact)
        .filter(Contact.id.in_(contact_ids))
        .order_by(Contact.updated_at.desc())
        .all()
    )
    results = [contact_to_dict(c) for c in contacts]
    if min_confidence is not None:
        results = [r for r in results if r["confidence"] >= min_confidence]
    return results[offset : offset + limit]


def get_contact_by_id(db: Session, contact_id: int) -> dict | None:
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return None
    return contact_to_dict(contact)


def set_contact_review_status(db: Session, contact_id: int, status: str) -> dict | None:
    if status not in {"pending", "confirmed", "rejected"}:
        raise ValueError(f"Invalid review status: {status}")
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return None
    contact.review_status = status
    contact.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(contact)
    return contact_to_dict(contact)


def bulk_set_contact_review_status(
    db: Session,
    contact_ids: list[int],
    status: str,
) -> dict:
    if status not in {"pending", "confirmed", "rejected"}:
        raise ValueError(f"Invalid review status: {status}")
    if not contact_ids:
        return {"updated": 0, "not_found": []}

    unique_ids = list(dict.fromkeys(contact_ids))
    contacts = db.query(Contact).filter(Contact.id.in_(unique_ids)).all()
    found_ids = {c.id for c in contacts}
    not_found = [cid for cid in unique_ids if cid not in found_ids]

    now = datetime.utcnow()
    for contact in contacts:
        contact.review_status = status
        contact.updated_at = now

    db.commit()
    return {"updated": len(contacts), "not_found": not_found}


def count_contacts(db: Session, *, since: datetime | None = None, review_status: str | None = None) -> int:
    query = db.query(Contact)
    if review_status:
        query = query.filter(Contact.review_status == review_status)
    if since:
        query = (
            query.join(PersonMention)
            .join(Article)
            .filter(Article.scraped_at >= since)
            .distinct()
        )
    return query.count()


def cleanup_invalid_contacts(db: Session) -> int:
    removed = 0
    for contact in db.query(Contact).all():
        if not is_valid_person_name(contact.full_name, allow_single_word=True):
            db.delete(contact)
            removed += 1
            continue
        if not contact.mentions:
            db.delete(contact)
            removed += 1
    if removed:
        db.commit()
    return removed


def delete_mentions_for_article(db: Session, article_id: int) -> int:
    count = db.query(PersonMention).filter(PersonMention.article_id == article_id).delete()
    return count


def migrate_legacy_people(db: Session) -> int:
    """Migrate legacy `people` rows into contacts + mentions."""
    if db.query(PersonMention).count() > 0:
        return 0

    migrated = 0
    for legacy in db.query(Person).all():
        result = save_mention(
            db,
            legacy.article_id,
            {
                "full_name": legacy.full_name,
                "role_context": legacy.role_context or "",
                "mention_count": legacy.mention_count,
                "sources": ["legacy"],
                "confidence": 0.7,
            },
        )
        if result:
            migrated += 1
    if migrated:
        db.commit()
        logger.info("Migrated %d legacy person rows to contacts", migrated)
    return migrated


def get_stats_contacts(db: Session) -> dict:
    total_articles = db.query(Article).count()
    total_people = count_contacts(db, review_status="confirmed") + count_contacts(db, review_status="pending")
    pending_review = count_contacts(db, review_status="pending")
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_articles = db.query(Article).filter(Article.scraped_at >= last_24h).count()
    recent_people = count_contacts(db, since=last_24h)
    return {
        "total_articles": total_articles,
        "total_people": total_people,
        "people_last_24h": recent_people,
        "articles_last_24h": recent_articles,
        "pending_review": pending_review,
    }
