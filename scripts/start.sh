#!/bin/bash
set -e

cd "$(dirname "$0")/.."

# Create data directory for SQLite
mkdir -p data

# Copy .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
fi

exec uvicorn app.main:app --host "${ACS_HOST:-0.0.0.0}" --port "${ACS_PORT:-8900}"
