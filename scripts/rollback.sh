#!/usr/bin/env bash
# Roll back to the previously deployed release tag recorded by deploy.sh.
# Limitation: this rolls back the APPLICATION images only. Database migrations
# are not automatically reverted (see docs/runbooks/rollback.md) — only
# forward-compatible schema changes are safe to roll an app version back
# against.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

STATE_DIR="infra/compose"
PREVIOUS_FILE="$STATE_DIR/PREVIOUS_RELEASE"
CURRENT_FILE="$STATE_DIR/CURRENT_RELEASE"

if [ ! -f "$PREVIOUS_FILE" ]; then
  echo "No previous release recorded. Nothing to roll back to." >&2
  exit 1
fi

RELEASE_TAG="$(cat "$PREVIOUS_FILE")"
echo "Rolling back to release ${RELEASE_TAG}..."
export RELEASE_TAG
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d backend outbox-relay diagnosis-worker missing-telemetry-checker frontend

for i in $(seq 1 30); do
  if curl -fs http://localhost:8000/health > /dev/null 2>&1; then
    echo "backend healthy after rollback."
    break
  fi
  sleep 2
  if [ "$i" -eq 30 ]; then
    echo "backend did not become healthy after rollback." >&2
    exit 1
  fi
done

echo "$RELEASE_TAG" > "$CURRENT_FILE"
echo "Rolled back to: $RELEASE_TAG"
