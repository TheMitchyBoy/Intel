#!/bin/sh
set -e

echo "Initializing database..."
python -m src.main init

PORT="${PORT:-8000}"
echo "Starting server on port ${PORT}..."
exec uvicorn src.api.server:app --host 0.0.0.0 --port "${PORT}"
