# Runbook: dead-letter queue handling

## How a message gets here
The diagnosis worker retries a failing message via `readings.retry` (a
TTL-based delay queue that redelivers to `readings.process` automatically)
up to `MAX_DELIVERY_ATTEMPTS` (default 3) times. After that, it publishes the
message to `readings.dead-letter` instead of retrying again, and acks the
original delivery so it stops looping.

## Inspect dead-lettered messages

```bash
curl -s -u "$RABBITMQ_DEFAULT_USER:$RABBITMQ_DEFAULT_PASS" \
  http://localhost:15672/api/queues/%2F/readings.dead-letter | python -m json.tool
```

Or use the RabbitMQ management UI (http://localhost:15672) → Queues →
`readings.dead-letter` → "Get messages" to inspect payloads without
consuming them.

## Demonstrating this deliberately

`tests/e2e/test_poison_dead_letter.py` publishes a message with a
`_poison: true` marker directly onto `readings.process`. The diagnosis
worker's `handle_delivery()` treats that marker as an unconditional failure
(see `worker/diagnosis_consumer.py`), so the message predictably exhausts its
retries and lands in `readings.dead-letter` — a controlled, repeatable way to
exercise the dead-letter path without needing a "real" bug.

## Redriving a dead-lettered message (manual)

There is no automated redrive tool in this project (out of scope for the
brief). To manually redrive a message after fixing the underlying issue, use
the RabbitMQ management UI's "Get messages" (with requeue) on
`readings.dead-letter`, then re-publish the payload to the `telemetry.exchange`
with routing key `reading` using the management UI's "Publish message" panel.
