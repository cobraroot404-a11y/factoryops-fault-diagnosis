#!/usr/bin/env bash
# Start the full local stack (Postgres, RabbitMQ, backend, outbox relay,
# diagnosis worker, missing-telemetry checker, frontend, Prometheus, Grafana).
# The simulator is NOT started by this script — run scripts/run-simulator.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

./scripts/generate-local-env.sh
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d --build \
  postgres rabbitmq backend outbox-relay diagnosis-worker missing-telemetry-checker frontend prometheus grafana

echo
echo "Waiting for backend health check..."
docker compose -f infra/compose/docker-compose.yml --env-file .env ps

echo
echo "Frontend:    http://localhost:5173"
echo "Backend API: http://localhost:8000/docs"
echo "RabbitMQ UI: http://localhost:15672"
echo "Prometheus:  http://localhost:9090"
echo "Grafana:     http://localhost:3000"
echo
echo "Next: ./scripts/migrate.sh && ./scripts/seed.sh && ./scripts/run-simulator.sh"
