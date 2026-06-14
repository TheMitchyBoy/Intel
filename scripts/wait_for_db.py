"""Wait for PostgreSQL and validate DATABASE_URL before startup."""

import sys

from sqlalchemy import create_engine, text

from src.config import settings


def wait_for_db(max_attempts: int = 30, delay_seconds: int = 2) -> bool:
    if not settings.database_is_configured():
        try:
            settings.validate_database_config()
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
        return False

    url = settings.resolved_database_url()
    print(f"Connecting to database at {url.split('@')[-1] if '@' in url else '...'}")

    import time

    for attempt in range(1, max_attempts + 1):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database connection OK")
            return True
        except Exception as exc:
            print(f"Database not ready ({attempt}/{max_attempts}): {exc}")
            if attempt == max_attempts:
                print(f"ERROR: Could not connect to database: {exc}", file=sys.stderr)
                return False
            time.sleep(delay_seconds)

    return False


if __name__ == "__main__":
    ok = wait_for_db()
    sys.exit(0 if ok else 1)
