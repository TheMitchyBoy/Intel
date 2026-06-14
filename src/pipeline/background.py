"""Run scrape pipeline in a background thread so HTTP requests don't time out."""

import logging
import threading
from typing import Any, Optional

from src.database.models import get_session_factory
from src.pipeline.runner import run_pipeline

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_running = False
_result: Optional[dict[str, Any]] = None
_error: Optional[str] = None


def scrape_status() -> dict[str, Any]:
    with _lock:
        return {
            "running": _running,
            "result": _result,
            "error": _error,
        }


def start_background_scrape() -> dict[str, str]:
    global _running, _result, _error

    with _lock:
        if _running:
            return {"status": "already_running", "message": "A scrape is already in progress."}
        _running = True
        _result = None
        _error = None

    def _run() -> None:
        global _running, _result, _error
        db = get_session_factory()()
        try:
            result = run_pipeline(db)
            with _lock:
                _result = result
        except Exception as exc:
            logger.exception("Background scrape failed")
            with _lock:
                _error = str(exc)
        finally:
            db.close()
            with _lock:
                _running = False

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "message": "Scrape started in background."}
