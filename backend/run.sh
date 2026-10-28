#!/usr/bin/env bash
# SirenSync Backend Startup Script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
export PYTHONPATH="$DIR"
exec "$DIR/venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --reload
