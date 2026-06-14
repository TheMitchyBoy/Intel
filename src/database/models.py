from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

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

    def to_dict(self) -> dict:
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
            "people": [p.to_dict() for p in self.people],
        }


class Person(Base):
    """Person mentioned in a newspaper article — CRM-ready contact record."""

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


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
