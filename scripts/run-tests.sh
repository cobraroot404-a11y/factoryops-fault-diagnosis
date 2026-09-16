#!/usr/bin/env bash
# Run the test suite against a LIVE local stack (start it first with
# ./scripts/start.sh, then ./scripts/migrate.sh && ./scripts/seed.sh).
#
# Usage:
#   ./scripts/run-tests.sh            # unit + integration tests (fast)
#   ./scripts/run-tests.sh --e2e      # also runs the worker-stop/backlog and
#                                      # poison-message/dead-letter demonstrations
#                                      # (stops/restarts the diagnosis-worker container)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a; source .env; set +a
fi

export BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://localhost:8000}"
export DATABASE_URL="postgresql+psycopg://${POSTGRES_USER:-factoryops}:${POSTGRES_PASSWORD:-changeme-local-only}@localhost:5432/${POSTGRES_DB:-factoryops}"
export RABBITMQ_URL="amqp://${RABBITMQ_DEFAULT_USER:-factoryops}:${RABBITMQ_DEFAULT_PASS:-changeme-local-only}@localhost:5672/"

VENV_DIR=".venv-test"
if [ ! -d "$VENV_DIR" ]; then
  python -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/Scripts/activate" 2>/dev/null || source "$VENV_DIR/bin/activate"

pip install --quiet --disable-pip-version-check -r backend/requirements-dev.txt -r tests/e2e/requirements.txt

echo "== ruff lint (backend) =="
ruff check backend/app worker simulator scripts/fault_ctl.py

echo "== pure unit tests (rule engine) =="
pytest tests/worker -v

echo "== backend/API integration tests (live stack) =="
pytest tests/backend -v

if [ "${1:-}" = "--e2e" ]; then
  echo "== e2e demonstrations (worker stop/backlog, poison/dead-letter) =="
  pytest tests/e2e -v -s
fi
