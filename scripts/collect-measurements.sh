#!/usr/bin/env bash
# Run scripts/measure.py against the live local stack (start it first).
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; source .env; set +a; fi
export BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://localhost:8000}"
export DATABASE_URL="postgresql+psycopg://${POSTGRES_USER:-factoryops}:${POSTGRES_PASSWORD:-changeme-local-only}@localhost:5432/${POSTGRES_DB:-factoryops}"

VENV_DIR=".venv-test"
if [ ! -d "$VENV_DIR" ]; then python -m venv "$VENV_DIR"; fi
source "$VENV_DIR/Scripts/activate" 2>/dev/null || source "$VENV_DIR/bin/activate"
pip install --quiet --disable-pip-version-check -r backend/requirements-dev.txt

python scripts/measure.py
