"""Run scrape pipeline in a background thread with DB-backed status."""

import json
import logging
import threading
from typing import Any

from src.database import crud
from src.database.models import get_session_factory
from src.pipeline.runner import run_pipeline

logger = logging.getLogger(__name__)


def _pipeline_result_from_run(run) -> dict[str, Any]:
    if run.result_json:
        try:
            return json.loads(run.result_json)
        except json.JSONDecodeError:
            pass
    return {}


def scrape_status(run_id: int | None = None) -> dict[str, Any]:
    db = get_session_factory()()
    try:
        run = crud.get_pipeline_run(db, run_id) if run_id else crud.get_latest_pipeline_run(db)
        if not run:
            return {"running": False, "run_id": None, "result": None, "error": None}

        if run.status == "running":
            return {"running": True, "run_id": run.id, "result": None, "error": None}

        return {
            "running": False,
            "run_id": run.id,
            "result": _pipeline_result_from_run(run) or None,
            "error": run.error_message,
        }
    finally:
        db.close()


def start_background_scrape() -> dict[str, Any]:
    db = get_session_factory()()
    try:
        run = crud.create_pipeline_run(db)
        if run is None:
            latest = crud.get_latest_pipeline_run(db)
            return {
                "status": "already_running",
                "message": "A scrape is already in progress.",
                "run_id": latest.id if latest else None,
            }
        run_id = run.id
    finally:
        db.close()

    def _run() -> None:
        db = get_session_factory()()
        try:
            result = run_pipeline(db)
            crud.finish_pipeline_run(db, run_id, result=result)
        except Exception as exc:
            logger.exception("Background scrape failed for run %s", run_id)
            crud.finish_pipeline_run(db, run_id, error=str(exc))
        finally:
            db.close()

    threading.Thread(target=_run, daemon=True, name=f"scrape-{run_id}").start()
    return {
        "status": "started",
        "message": "Scrape started in background.",
        "run_id": run_id,
    }
