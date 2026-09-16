#!/usr/bin/env bash
# Stop all services WITHOUT deleting data volumes (Postgres/RabbitMQ/Grafana/
# Prometheus data survives). Use scripts/cleanup-demo-data.sh to wipe demo data.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f infra/compose/docker-compose.yml --env-file .env --profile simulate stop
echo "All services stopped. Data volumes preserved. Restart with ./scripts/start.sh"
