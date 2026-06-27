import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.config import settings
from src.database import contacts
from src.database.crud import (
    cleanup_invalid_people,
    get_article_by_id,
    get_articles,
    get_people_grouped,
    get_person_grouped,
    get_stats,
)
from src.database.models import get_db, get_session_factory, init_db
from src.database.url import database_setup_error
from src.pipeline.background import scrape_status, start_background_reprocess, start_background_scrape
from src.pipeline.scheduler import schedule_info, start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_is_configured():
        try:
            init_db()
            db = get_session_factory()()
            try:
                contacts.migrate_legacy_people(db)
                removed = cleanup_invalid_people(db)
                if removed:
                    logger.info("Cleaned up %d invalid contacts on startup", removed)
            finally:
                db.close()
        except Exception as exc:
            print(f"WARNING: Database init failed: {exc}")
    else:
        print("WARNING: Database not configured — API data endpoints will return 503")

    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Intel — Newspaper Intelligence API",
    description="CRM-ready API for scraped local newspaper data with AI summaries and people mentions.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


def require_database():
    if not settings.database_is_configured():
        raise HTTPException(status_code=503, detail=database_setup_error())
    return True


def _since_from_params(since: Optional[datetime], hours: Optional[int]) -> Optional[datetime]:
    if since is not None:
        return since
    if hours is not None:
        return datetime.utcnow() - timedelta(hours=hours)
    return None


class PersonArticleRef(BaseModel):
    mention_id: int
    article_id: int
    title: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    scraped_at: Optional[str] = None
    mention_count: int = 1
    role_context: Optional[str] = None
    confidence: Optional[float] = None
    sources: list[str] = []


class PersonResponse(BaseModel):
    id: int
    full_name: str
    role_context: Optional[str] = None
    mention_count: int
    article_count: int = 1
    confidence: float = 0.5
    sources: list[str] = []
    review_status: str = "pending"
    created_at: Optional[str] = None
    latest_seen: Optional[str] = None
    article_id: Optional[int] = None
    article_title: Optional[str] = None
    article_url: Optional[str] = None
    article_summary: Optional[str] = None
    articles: list[PersonArticleRef] = []


class ReviewRequest(BaseModel):
    status: str


class BulkReviewRequest(BaseModel):
    ids: list[int]
    status: str


class RenameRequest(BaseModel):
    full_name: str


class BulkReviewResponse(BaseModel):
    updated: int
    not_found: list[int] = []


class StatsResponse(BaseModel):
    total_articles: int
    total_people: int
    articles_last_24h: int
    people_last_24h: int
    pending_review: int = 0


class ArticleResponse(BaseModel):
    id: int
    source_name: str
    title: str
    url: str
    summary: Optional[str] = None
    published_at: Optional[str] = None
    scraped_at: Optional[str] = None
    region: Optional[str] = None
    status: str
    people: list[dict] = []


class PipelineResult(BaseModel):
    sources: int
    found: int
    new: int
    duplicates: int = 0
    skipped_not_today: int = 0
    people: int
    errors: list[dict]


class ScrapeTriggerResponse(BaseModel):
    status: str
    message: str
    run_id: Optional[int] = None


class ScrapeStatusResponse(BaseModel):
    running: bool
    run_id: Optional[int] = None
    result: Optional[dict] = None
    error: Optional[str] = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "intel",
        "database": "connected" if settings.database_is_configured() else "not_configured",
        "scrape_schedule": schedule_info(),
    }


@app.get("/api/v1/setup")
def setup_status():
    """Public endpoint — shows whether Postgres is connected (no API key required)."""
    configured = settings.database_is_configured()
    return {
        "database_configured": configured,
        "diagnostics": settings.database_diagnostics(),
        "scrape_schedule": schedule_info(),
        "instructions": None if configured else database_setup_error(),
    }


@app.get("/api/v1/stats", response_model=StatsResponse, dependencies=[Depends(verify_api_key), Depends(require_database)])
def stats(db: Session = Depends(get_db)):
    return get_stats(db)


@app.get("/api/v1/articles", response_model=list[ArticleResponse], dependencies=[Depends(verify_api_key), Depends(require_database)])
def list_articles(
    source: Optional[str] = None,
    region: Optional[str] = None,
    since: Optional[datetime] = None,
    hours: Optional[int] = Query(None, ge=1, le=168),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    since_cutoff = _since_from_params(since, hours)
    articles = get_articles(db, source=source, region=region, since=since_cutoff, limit=limit, offset=offset)
    return [a.to_dict() for a in articles]


@app.get("/api/v1/articles/{article_id}", response_model=ArticleResponse, dependencies=[Depends(verify_api_key), Depends(require_database)])
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article.to_dict()


@app.get("/api/v1/people", response_model=list[PersonResponse], dependencies=[Depends(verify_api_key), Depends(require_database)])
def list_people(
    name: Optional[str] = None,
    since: Optional[datetime] = None,
    hours: Optional[int] = Query(None, ge=1, le=168),
    review_status: Optional[str] = Query(None, pattern="^(pending|confirmed|rejected)$"),
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    since_cutoff = _since_from_params(since, hours)
    return get_people_grouped(
        db,
        name=name,
        since=since_cutoff,
        review_status=review_status,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )


@app.post("/api/v1/people/review/bulk", response_model=BulkReviewResponse, dependencies=[Depends(verify_api_key), Depends(require_database)])
def bulk_review_people(body: BulkReviewRequest, db: Session = Depends(get_db)):
    try:
        return contacts.bulk_set_contact_review_status(db, body.ids, body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/v1/people/{contact_id}/review", response_model=PersonResponse, dependencies=[Depends(verify_api_key), Depends(require_database)])
def review_person(contact_id: int, body: ReviewRequest, db: Session = Depends(get_db)):
    try:
        result = contacts.set_contact_review_status(db, contact_id, body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not result:
        raise HTTPException(status_code=404, detail="Person not found")
    return result


@app.patch("/api/v1/people/{contact_id}", response_model=PersonResponse, dependencies=[Depends(verify_api_key), Depends(require_database)])
def rename_person(contact_id: int, body: RenameRequest, db: Session = Depends(get_db)):
    try:
        result = contacts.update_contact_name(db, contact_id, body.full_name)
    except contacts.NameConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not result:
        raise HTTPException(status_code=404, detail="Person not found")
    return result


@app.get("/api/v1/people/{person_id}", response_model=PersonResponse, dependencies=[Depends(verify_api_key), Depends(require_database)])
def get_person(person_id: int, db: Session = Depends(get_db)):
    person = get_person_grouped(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@app.post("/api/v1/reprocess/names", response_model=ScrapeTriggerResponse, dependencies=[Depends(verify_api_key), Depends(require_database)])
def reprocess_names():
    """Re-run name extraction on all stored articles."""
    return start_background_reprocess()


@app.get("/api/v1/reprocess/status", response_model=ScrapeStatusResponse, dependencies=[Depends(verify_api_key), Depends(require_database)])
def reprocess_status(run_id: Optional[int] = None):
    return scrape_status(run_id)


@app.post("/api/v1/scrape", response_model=ScrapeTriggerResponse, dependencies=[Depends(verify_api_key), Depends(require_database)])
def trigger_scrape():
    """Start a scrape run in the background (avoids Railway/proxy timeouts)."""
    return start_background_scrape()


@app.get("/api/v1/scrape/status", response_model=ScrapeStatusResponse, dependencies=[Depends(verify_api_key), Depends(require_database)])
def scrape_run_status(run_id: Optional[int] = None):
    """Poll scrape progress after POST /api/v1/scrape."""
    return scrape_status(run_id)


@app.get("/api/v1/export/people", dependencies=[Depends(verify_api_key), Depends(require_database)])
def export_people(
    since: Optional[datetime] = None,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    """Export people data for CRM import."""
    people = get_people_grouped(db, since=since, limit=10000)

    if format == "csv":
        import csv
        import io

        flat = [
            {
                "full_name": p["full_name"],
                "role_context": p.get("role_context"),
                "mention_count": p["mention_count"],
                "article_count": p["article_count"],
                "latest_article": p.get("article_title"),
                "article_url": p.get("article_url"),
            }
            for p in people
        ]
        output = io.StringIO()
        if flat:
            writer = csv.DictWriter(output, fieldnames=flat[0].keys())
            writer.writeheader()
            writer.writerows(flat)
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(output.getvalue(), media_type="text/csv")

    return people


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built React CRM from / when static files are present."""
    if not STATIC_DIR.is_dir() or not (STATIC_DIR / "index.html").is_file():
        return

    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    def _spa_index() -> HTMLResponse:
        index = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        script = (
            f"<script>window.__INTEL_API_KEY__={json.dumps(settings.api_key)};</script>"
        )
        if "</head>" in index:
            index = index.replace("</head>", f"{script}</head>", 1)
        else:
            index = script + index
        return HTMLResponse(index)

    @app.get("/favicon.svg", include_in_schema=False)
    def favicon():
        return FileResponse(STATIC_DIR / "favicon.svg")

    @app.get("/", include_in_schema=False)
    def spa_root():
        return _spa_index()

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = STATIC_DIR / path
        if file_path.is_file():
            return FileResponse(file_path)
        return _spa_index()


_mount_frontend(app)
