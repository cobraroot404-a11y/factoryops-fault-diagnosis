# Runbook: diagnosis-worker backlog recovery

## When this applies
The `diagnosis-worker` container is stopped or crashes while readings are
still being ingested. Ingestion never stops accepting readings (they land in
the transactional outbox and then RabbitMQ regardless of whether the worker
is up), so a backlog builds in the `readings.process` queue.

## Observe the backlog

```bash
open http://localhost:15672   # RabbitMQ management UI, log in with your .env credentials
# or:
curl -s -u "$RABBITMQ_DEFAULT_USER:$RABBITMQ_DEFAULT_PASS" \
  http://localhost:15672/api/queues/%2F/readings.process | python -m json.tool
```

Watch the `messages` count on `readings.process` grow, and the Grafana panel
"Readings processed / sec" flatten to zero on the FactoryOps Overview
dashboard (http://localhost:3000).

## Restore

```bash
docker compose -f infra/compose/docker-compose.yml --env-file .env start diagnosis-worker
```

The worker resumes consuming from where the queue left off. Because every
message carries a stable id and the worker checks `processed_messages` before
doing any state mutation, draining the backlog is safe: no incident is
opened twice, and readings that were already fully processed before the
worker stopped (if any were mid-flight) are simply skipped as duplicates.

This exact sequence — stop worker, grow backlog, restore, confirm safe,
duplicate-free drain — is exercised automatically in
`tests/e2e/test_backlog_recovery.py` (run via `./scripts/run-tests.sh --e2e`).
