#!/usr/bin/env bash
# Local CD: build+tag a versioned release from the current git commit, apply
# migrations, verify health, and record the deployed version for rollback.
# No remote registry involved — images are tagged and kept in this machine's
# local Docker image cache.
set -euo pipefail
cd "$(dirname "$0")/.."

./scripts/generate-local-env.sh
set -a; source .env; set +a

RELEASE_TAG="${1:-$(git rev-parse --short HEAD)}"
STATE_DIR="infra/compose"
CURRENT_FILE="$STATE_DIR/CURRENT_RELEASE"
PREVIOUS_FILE="$STATE_DIR/PREVIOUS_RELEASE"

if [ -f "$CURRENT_FILE" ]; then
  cp "$CURRENT_FILE" "$PREVIOUS_FILE"
fi

echo "Deploying release ${RELEASE_TAG}..."
export RELEASE_TAG
docker compose -f infra/compose/docker-compose.yml --env-file .env build backend outbox-relay diagnosis-worker missing-telemetry-checker frontend
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d postgres rabbitmq
docker compose -f infra/compose/docker-compose.yml --env-file .env run --rm backend alembic upgrade head
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d backend outbox-relay diagnosis-worker missing-telemetry-checker frontend prometheus grafana

echo "Waiting for backend health check..."
for i in $(seq 1 30); do
  if curl -fs http://localhost:8000/health > /dev/null 2>&1; then
    echo "backend healthy."
    break
  fi
  sleep 2
  if [ "$i" -eq 30 ]; then
    echo "backend did not become healthy in time." >&2
    exit 1
  fi
done

echo "$RELEASE_TAG" > "$CURRENT_FILE"
echo "Deployed and verified release: $RELEASE_TAG"
echo "Rollback with: ./scripts/rollback.sh"
