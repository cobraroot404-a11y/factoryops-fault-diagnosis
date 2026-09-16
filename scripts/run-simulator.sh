#!/usr/bin/env bash
# Start the telemetry simulator (SIMULATED DATA ONLY — no physical hardware involved).
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f infra/compose/docker-compose.yml --env-file .env --profile simulate up -d --build simulator
echo "Simulator running. Tail logs with: docker compose -f infra/compose/docker-compose.yml logs -f simulator"
