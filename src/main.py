"""Intel — Local Newspaper Intelligence Scraper CLI."""

import logging

import typer
from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import settings
from src.database.models import SessionLocal, init_db
from src.pipeline.runner import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Intel — Scrape local newspapers, extract names, summarize with AI.")


@app.command()
def init():
    """Initialize the database tables."""
    init_db()
    typer.echo("Database initialized.")


@app.command()
def scrape():
    """Run a single scrape cycle."""
    init_db()
    db = SessionLocal()
    try:
        result = run_pipeline(db)
        typer.echo(f"Done: {result['new']} new articles, {result['people']} people found.")
        if result["errors"]:
            typer.echo(f"Errors: {result['errors']}", err=True)
    finally:
        db.close()


@app.command()
def scheduler():
    """Run the scraper on a schedule."""
    init_db()
    sched = BlockingScheduler()

    def job():
        db = SessionLocal()
        try:
            result = run_pipeline(db)
            logger.info("Scheduled scrape complete: %s", result)
        finally:
            db.close()

    sched.add_job(job, "interval", hours=settings.scrape_interval_hours, id="scrape_job")
    logger.info("Scheduler started — scraping every %d hours", settings.scrape_interval_hours)
    sched.start()


@app.command()
def serve():
    """Start the API server."""
    import uvicorn
    uvicorn.run("src.api.server:app", host=settings.api_host, port=settings.api_port, reload=False)


if __name__ == "__main__":
    app()
