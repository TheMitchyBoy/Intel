#!/bin/sh
set -e

echo "Checking database connection..."
if python scripts/wait_for_db.py; then
  echo "Initializing database..."
  python -m src.main init
else
  echo ""
  echo "WARNING: Database not available — starting web server anyway."
  echo "Add PostgreSQL in Railway, connect it to Throughline, then redeploy."
  echo ""
fi

PORT="${PORT:-8000}"
echo "Starting server on port ${PORT}..."
exec uvicorn src.api.server:app --host 0.0.0.0 --port "${PORT}"
