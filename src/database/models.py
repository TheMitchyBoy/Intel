import json
from datetime import datetime
from functools import lru_cache

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from src.config import settings


class Base(DeclarativeBase):
    pass


class Article(Base):
    """Scraped newspaper article with AI-generated summary."""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(255), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    original_content = Column(Text)
    summary = Column(Text)
    published_at = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    region = Column(String(100))
    status = Column(String(50), default="processed")

    people = relationship("Person", back_populates="article", cascade="all, delete-orphan")
    mentions = relationship("PersonMention", back_populates="article", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        mention_people = [m.to_brief_dict() for m in self.mentions] if self.mentions else [p.to_dict() for p in self.people]
        return {
            "id": self.id,
            "source_name": self.source_name,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "region": self.region,
            "status": self.status,
            "people": mention_people,
        }


class Contact(Base):
    """Canonical person record — one contact, many article mentions."""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False, index=True)
    name_key = Column(String(255), nullable=False, unique=True, index=True)
    review_status = Column(String(20), default="pending", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    mentions = relationship("PersonMention", back_populates="contact", cascade="all, delete-orphan")


class PersonMention(Base):
    """A person mentioned in a specific article."""

    __tablename__ = "person_mentions"
    __table_args__ = (UniqueConstraint("contact_id", "article_id", name="uq_contact_article"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    role_context = Column(Text)
    mention_count = Column(Integer, default=1)
    confidence = Column(Float, default=0.5, nullable=False)
    sources = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    contact = relationship("Contact", back_populates="mentions")
    article = relationship("Article", back_populates="mentions")

    def sources_list(self) -> list[str]:
        try:
            return json.loads(self.sources or "[]")
        except json.JSONDecodeError:
            return []

    def to_brief_dict(self) -> dict:
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "article_id": self.article_id,
            "full_name": self.contact.full_name if self.contact else "",
            "role_context": self.role_context,
            "mention_count": self.mention_count,
            "confidence": self.confidence,
            "sources": self.sources_list(),
            "review_status": self.contact.review_status if self.contact else "pending",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "article_title": self.article.title if self.article else None,
            "article_url": self.article.url if self.article else None,
            "article_summary": self.article.summary if self.article else None,
        }


class Person(Base):
    """Legacy per-article person row (migrated to Contact + PersonMention)."""

    __tablename__ = "people"
    __table_args__ = (UniqueConstraint("article_id", "full_name", name="uq_person_article"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False, index=True)
    role_context = Column(Text)
    mention_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    article = relationship("Article", back_populates="people")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "article_id": self.article_id,
            "full_name": self.full_name,
            "role_context": self.role_context,
            "mention_count": self.mention_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "article_title": self.article.title if self.article else None,
            "article_url": self.article.url if self.article else None,
            "article_summary": self.article.summary if self.article else None,
        }


class ScrapeLog(Base):
    """Audit log for scrape runs."""

    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(255), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime)
    articles_found = Column(Integer, default=0)
    articles_new = Column(Integer, default=0)
    status = Column(String(50), default="running")
    error_message = Column(Text)


class PipelineRun(Base):
    """Tracks a full pipeline scrape job (shared across app instances)."""

    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime)
    status = Column(String(50), default="running", nullable=False, index=True)
    result_json = Column(Text)
    error_message = Column(Text)


@lru_cache
def get_engine() -> Engine:
    settings.validate_database_config()
    return create_engine(settings.resolved_database_url(), pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine())


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
