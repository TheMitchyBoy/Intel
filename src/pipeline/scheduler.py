"""Daily scrape scheduler — runs inside the API process on Railway."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import settings
from src.pipeline.background import start_background_scrape

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def schedule_info() -> dict:
    return {
        "enabled": settings.scrape_schedule_enabled,
        "hour": settings.scrape_schedule_hour,
        "minute": settings.scrape_schedule_minute,
        "timezone": settings.scrape_timezone,
    }


def _run_scheduled_scrape() -> None:
    if not settings.database_is_configured():
        logger.warning("Skipping scheduled scrape — database not configured")
        return
    result = start_background_scrape()
    logger.info("Scheduled scrape triggered: %s", result)


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler

    if not settings.scrape_schedule_enabled:
        logger.info("Daily scrape scheduler disabled")
        return None

    if not settings.database_is_configured():
        logger.warning("Daily scrape scheduler not started — database not configured")
        return None

    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=settings.scrape_timezone)
    _scheduler.add_job(
        _run_scheduled_scrape,
        CronTrigger(
            hour=settings.scrape_schedule_hour,
            minute=settings.scrape_schedule_minute,
            timezone=settings.scrape_timezone,
        ),
        id="daily_scrape",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Daily scrape scheduled at %02d:%02d %s",
        settings.scrape_schedule_hour,
        settings.scrape_schedule_minute,
        settings.scrape_timezone,
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Daily scrape scheduler stopped")
