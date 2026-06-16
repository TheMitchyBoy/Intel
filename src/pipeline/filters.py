"""Article filtering helpers for the scrape pipeline."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def is_published_today(published_at: datetime | None, tz_name: str) -> bool:
    """Return True if the article was published on today's calendar date in tz_name."""
    if published_at is None:
        return True

    tz = ZoneInfo(tz_name)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    return published_at.astimezone(tz).date() == datetime.now(tz).date()
