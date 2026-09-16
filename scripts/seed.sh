#!/usr/bin/env bash
# Seed two factories, demo users, and simulated motors. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f infra/compose/docker-compose.yml --env-file .env run --rm backend python seed.py
echo
echo "Demo credentials written to infra/compose/seed-output/demo-credentials.json (gitignored, local only)."
