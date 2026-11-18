#!/usr/bin/env bash
# SirenSync Unified Backend Startup Script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(cd "$DIR/.." >/dev/null 2>&1 && pwd)"
export PYTHONPATH="$ROOT_DIR:$DIR"
exec "$DIR/venv/bin/uvicorn" backend.main:app --host 0.0.0.0 --port 8000 --reload
