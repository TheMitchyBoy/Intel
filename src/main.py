"""Intel — Local Newspaper Intelligence Scraper CLI."""

import logging

import typer

from src.config import settings
from src.database.models import get_session_factory, init_db
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
    db = get_session_factory()()
    try:
        result = run_pipeline(db)
        typer.echo(f"Done: {result['new']} new articles, {result['people']} people found.")
        if result["errors"]:
            typer.echo(f"Errors: {result['errors']}", err=True)
    finally:
        db.close()


@app.command()
def scheduler():
    """Run the scraper on a daily schedule (standalone worker)."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    from src.pipeline.scheduler import _run_scheduled_scrape

    init_db()
    sched = BlockingScheduler(timezone=settings.scrape_timezone)
    sched.add_job(
        _run_scheduled_scrape,
        CronTrigger(
            hour=settings.scrape_schedule_hour,
            minute=settings.scrape_schedule_minute,
            timezone=settings.scrape_timezone,
        ),
        id="daily_scrape",
    )
    logger.info(
        "Scheduler started — daily scrape at %02d:%02d %s (today's articles only)",
        settings.scrape_schedule_hour,
        settings.scrape_schedule_minute,
        settings.scrape_timezone,
    )
    sched.start()


@app.command()
def serve():
    """Start the API server."""
    import uvicorn

    uvicorn.run("src.api.server:app", host=settings.api_host, port=settings.port, reload=False)


if __name__ == "__main__":
    app()
