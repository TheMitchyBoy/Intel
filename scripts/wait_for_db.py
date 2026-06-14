"""Wait for PostgreSQL and validate DATABASE_URL before startup."""

import os
import sys
import time

from sqlalchemy import create_engine, text

from src.config import settings


def wait_for_db(max_attempts: int = 30, delay_seconds: int = 2) -> None:
    settings.validate_database_config()

    url = settings.database_url
    print(f"Connecting to database at {url.split('@')[-1] if '@' in url else '...'}")

    for attempt in range(1, max_attempts + 1):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database connection OK")
            return
        except Exception as exc:
            print(f"Database not ready ({attempt}/{max_attempts}): {exc}")
            if attempt == max_attempts:
                raise
            time.sleep(delay_seconds)


if __name__ == "__main__":
    try:
        wait_for_db()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Could not connect to database: {exc}", file=sys.stderr)
        sys.exit(1)
