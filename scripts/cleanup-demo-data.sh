#!/usr/bin/env bash
# Explicitly wipe ALL FactoryOps demo data (factories, users, machines,
# readings, incidents, tickets, fault injections, outbox/queue state) and the
# local seed-output secrets. This does NOT touch source code, git history, or
# any other project. Requires --yes to actually run.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" != "--yes" ]; then
  echo "This permanently deletes all FactoryOps demo data in the local database."
  echo "Re-run as: ./scripts/cleanup-demo-data.sh --yes"
  exit 1
fi

docker compose -f infra/compose/docker-compose.yml --env-file .env run --rm backend python -c "
from sqlalchemy import text
from app.db import engine
tables = ['processed_messages','outbox_events','machine_fault_state','fault_injections','incidents','tickets','readings','machines','users','factories']
with engine.begin() as conn:
    for t in tables:
        conn.execute(text(f'TRUNCATE TABLE {t} RESTART IDENTITY CASCADE'))
print('All FactoryOps demo data truncated.')
"

rm -rf infra/compose/seed-output
echo "Removed infra/compose/seed-output (demo credentials + machine keys)."
echo "Re-seed with: ./scripts/seed.sh"
