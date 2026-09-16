# FactoryOps measurements

Run at: 2026-09-16T21:42:52.571539+00:00 (UTC)
Raw data: [run-20260916T214252Z.json](../measurements/run-20260916T214252Z.json)

All telemetry is **simulated**, generated locally by `simulator/simulate.py` and
fed through the real ingestion -> outbox -> RabbitMQ -> diagnosis-worker
pipeline running in Docker Compose on this machine. Nothing here has been
validated against physical manufacturing equipment.

## Detection & recovery latency

| Metric | Value |
|---|---|
| Fault injection to detection | 1.062 s |
| Fault removal to verified recovery | 1.157 s |

Detection requires 3 consecutive breaching readings
(persistence window). Recovery requires 5 consecutive healthy
readings (separate, larger healthy-observation window) — this is why recovery
latency is intentionally longer than detection latency.

## Ingest throughput

| Metric | Value |
|---|---|
| Readings sent | 50 |
| Readings accepted | 50 |
| Accept success rate | 100.0% |
| Ingest wall time for batch | 0.672 s |

## False-incident rate (healthy simulation)

| Metric | Value |
|---|---|
| Duration | 20 s |
| Healthy readings sent | 20 |
| Incidents opened | 0 |

## Limitations

- Single-machine, single-run measurement on a development laptop — not a load test and not statistically averaged across many runs.
- Latencies include this machine's own Docker Desktop overhead and are not representative of a production deployment's network/latency profile.
- Processing-drain wait time is an approximation (polled), not an exact per-message trace.
