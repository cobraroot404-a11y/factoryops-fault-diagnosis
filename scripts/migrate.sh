#!/usr/bin/env bash
# Initialize/upgrade the database schema via Alembic.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f infra/compose/docker-compose.yml --env-file .env run --rm backend alembic upgrade head
