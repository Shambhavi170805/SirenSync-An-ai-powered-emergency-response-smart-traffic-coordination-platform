#!/usr/bin/env bash
# Start the unified SirenSync API from the repository without hard-coded venv paths.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(cd "$DIR/.." >/dev/null 2>&1 && pwd)"
cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR:$DIR${PYTHONPATH:+:$PYTHONPATH}"
if [[ -x "$ROOT_DIR/.venv/bin/uvicorn" ]]; then
  exec "$ROOT_DIR/.venv/bin/uvicorn" backend.main:app --host 0.0.0.0 --port 8000 --reload
elif [[ -x "$ROOT_DIR/venv/bin/uvicorn" ]]; then
  exec "$ROOT_DIR/venv/bin/uvicorn" backend.main:app --host 0.0.0.0 --port 8000 --reload
else
  exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
fi
