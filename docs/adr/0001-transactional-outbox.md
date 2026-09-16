# ADR 0001: Transactional outbox for reading ingestion

## Status
Accepted

## Context
Readings must never be silently lost if RabbitMQ is briefly unavailable at
the moment a reading is accepted. Writing to Postgres and publishing to
RabbitMQ are two separate systems with no shared transaction, so a naive
"write, then publish" flow can accept a reading and then lose it forever if
the publish fails after the DB commit (or double-publish if it fails before).

## Decision
`/telemetry/readings` writes the `Reading` row and an `OutboxEvent` row in one
Postgres transaction. A dedicated `outbox-relay` process polls unpublished
outbox rows, publishes them to RabbitMQ with publisher confirms enabled, and
marks each row published only after the broker confirms receipt.

## Consequences
- An ingested reading is durable the instant the HTTP request returns 202,
  regardless of RabbitMQ's availability at that instant.
- There is a small, bounded delivery delay (the relay's poll interval, 1s by
  default) between "accepted" and "queued for diagnosis."
- The relay can crash and restart safely: on restart it simply resumes
  polling for `published_at IS NULL` rows.
- This does not by itself make consumption exactly-once — the diagnosis
  worker separately guards against duplicate delivery (see
  `processed_messages` and the message-id dedup in
  `worker/diagnosis_consumer.py`).
