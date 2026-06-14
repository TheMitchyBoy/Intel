import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.config import settings
from src.database.crud import get_article_by_id, get_articles, get_people, get_person_by_id, get_stats
from src.database.models import get_db, init_db
from src.pipeline.runner import run_pipeline

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


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


class PersonResponse(BaseModel):
    id: int
    article_id: int
    full_name: str
    role_context: Optional[str] = None
    mention_count: int
    created_at: Optional[str] = None
    article_title: Optional[str] = None
    article_url: Optional[str] = None
    article_summary: Optional[str] = None


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


class StatsResponse(BaseModel):
    total_articles: int
    total_people: int
    articles_last_24h: int
    people_last_24h: int


class PipelineResult(BaseModel):
    sources: int
    found: int
    new: int
    people: int
    errors: list[dict]


@app.get("/health")
def health():
    return {"status": "ok", "service": "intel"}


@app.get("/api/v1/stats", response_model=StatsResponse, dependencies=[Depends(verify_api_key)])
def stats(db: Session = Depends(get_db)):
    return get_stats(db)


@app.get("/api/v1/articles", response_model=list[ArticleResponse], dependencies=[Depends(verify_api_key)])
def list_articles(
    source: Optional[str] = None,
    region: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    articles = get_articles(db, source=source, region=region, since=since, limit=limit, offset=offset)
    return [a.to_dict() for a in articles]


@app.get("/api/v1/articles/{article_id}", response_model=ArticleResponse, dependencies=[Depends(verify_api_key)])
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article.to_dict()


@app.get("/api/v1/people", response_model=list[PersonResponse], dependencies=[Depends(verify_api_key)])
def list_people(
    name: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    people = get_people(db, name=name, since=since, limit=limit, offset=offset)
    return [p.to_dict() for p in people]


@app.get("/api/v1/people/{person_id}", response_model=PersonResponse, dependencies=[Depends(verify_api_key)])
def get_person(person_id: int, db: Session = Depends(get_db)):
    person = get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person.to_dict()


@app.post("/api/v1/scrape", response_model=PipelineResult, dependencies=[Depends(verify_api_key)])
def trigger_scrape(db: Session = Depends(get_db)):
    """Manually trigger a scrape run. Useful for CRM integrations."""
    return run_pipeline(db)


@app.get("/api/v1/export/people", dependencies=[Depends(verify_api_key)])
def export_people(
    since: Optional[datetime] = None,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    """Export people data for CRM import."""
    people = get_people(db, since=since, limit=10000)
    records = [p.to_dict() for p in people]

    if format == "csv":
        import csv
        import io

        output = io.StringIO()
        if records:
            writer = csv.DictWriter(output, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(output.getvalue(), media_type="text/csv")

    return records


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
