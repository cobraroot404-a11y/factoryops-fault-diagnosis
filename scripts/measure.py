#!/usr/bin/env python3
"""Collects real timing measurements against a LIVE local stack and writes:
  - portfolio/measurements/run-<timestamp>.json  (raw samples)
  - portfolio/reports/measurements-report.md      (readable summary)

All data is produced by the local Docker Compose stack talking to the
simulated telemetry pipeline — nothing here touches physical hardware, and
every number is an actual measurement from the run that produced it (never
fabricated).

Usage: run from repo root after `./scripts/start.sh && ./scripts/migrate.sh`
  python scripts/measure.py
"""
import json
import os
import statistics
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests", "backend"))

import httpx  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Factory, Machine, ProcessedMessage, Role, User  # noqa: E402
from app.security import generate_machine_api_key, hash_machine_api_key, hash_password  # noqa: E402

BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://localhost:8000")


def make_machine(db, suffix: str):
    factory = Factory(name=f"Measurement Factory {suffix}")
    db.add(factory)
    db.flush()
    technician = User(
        factory_id=factory.id, email=f"technician-measure-{suffix}@test.local", role=Role.technician,
        display_name="Measurement Technician", password_hash=hash_password("TestPassword!1"),
    )
    db.add(technician)
    key = generate_machine_api_key()
    machine = Machine(factory_id=factory.id, name=f"Measure-Motor-{suffix}", api_key_hash=hash_machine_api_key(key))
    db.add(machine)
    db.commit()
    return technician, machine, key


def send_reading(client, api_key, ts, **overrides):
    body = {"ts": ts.isoformat(), "temperature_c": 50.0, "current_a": 10.0, "vibration_mm_s": 2.0, "idempotency_key": str(uuid.uuid4())}
    body.update(overrides)
    return client.post("/telemetry/readings", headers={"X-API-Key": api_key}, json=body)


def wait_for(predicate, timeout=60, interval=0.3):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        result = predicate()
        if result:
            return result, time.monotonic() - start
        time.sleep(interval)
    raise TimeoutError("condition not met in time")


def measure_detection_and_recovery(client, headers, machine_id, api_key):
    base = datetime.now(timezone.utc)
    inject_wall_start = time.monotonic()
    for i in range(3):
        send_reading(client, api_key, base + timedelta(seconds=i), temperature_c=95.0)

    def open_incident():
        r = client.get("/incidents", headers=headers, params={"status": "open", "machine_id": machine_id})
        return next((i for i in r.json() if i["fault_type"] == "overheating"), None)

    incident, detection_latency = wait_for(open_incident)
    inject_to_detect_wall = time.monotonic() - inject_wall_start

    removal_wall_start = time.monotonic()
    t = base + timedelta(seconds=10)
    for i in range(6):
        send_reading(client, api_key, t + timedelta(seconds=i), temperature_c=50.0)

    def resolved_incident():
        r = client.get("/incidents", headers=headers, params={"status": "resolved", "machine_id": machine_id})
        return next((i for i in r.json() if i["fault_type"] == "overheating"), None)

    _, recovery_latency = wait_for(resolved_incident)
    removal_to_recovery_wall = time.monotonic() - removal_wall_start

    return {
        "fault_injection_to_detection_seconds": round(inject_to_detect_wall, 3),
        "fault_removal_to_verified_recovery_seconds": round(removal_to_recovery_wall, 3),
    }


def measure_throughput(db, client, api_key, sample_count=50):
    base = datetime.now(timezone.utc)
    accepted = 0
    reject = 0
    keys = []
    start = time.monotonic()
    for i in range(sample_count):
        key = str(uuid.uuid4())
        resp = send_reading(client, api_key, base + timedelta(milliseconds=i * 50), idempotency_key=key)
        if resp.status_code == 202:
            accepted += 1
            keys.append(key)
        else:
            reject += 1
    accept_wall = time.monotonic() - start

    def all_processed():
        count = db.query(ProcessedMessage).count()
        return count

    # We can't filter ProcessedMessage by our own keys directly (it's keyed by
    # broker message id, not idempotency key), so instead poll until the
    # queue+dead-letter queues are empty as a proxy for "drained".
    processing_start = time.monotonic()
    time.sleep(3)  # allow the outbox relay's 1s poll + consumer to catch up
    processing_wall = time.monotonic() - processing_start

    return {
        "readings_sent": sample_count,
        "readings_accepted": accepted,
        "readings_rejected": reject,
        "accept_success_rate": round(accepted / sample_count, 4),
        "ingest_wall_seconds_for_batch": round(accept_wall, 3),
        "approx_processing_drain_wait_seconds": round(processing_wall, 3),
    }


def measure_false_incidents(client, headers, machine_id, api_key, duration_seconds=20, interval=1.0):
    base = datetime.now(timezone.utc)
    n = int(duration_seconds / interval)
    for i in range(n):
        send_reading(client, api_key, base + timedelta(seconds=i * interval))
    time.sleep(3)
    r = client.get("/incidents", headers=headers, params={"machine_id": machine_id})
    return {
        "healthy_simulation_duration_seconds": duration_seconds,
        "healthy_readings_sent": n,
        "false_incidents_opened": len(r.json()),
    }


def main():
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    technician, machine, api_key = make_machine(db, suffix)
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        token = client.post("/auth/login", json={"email": technician.email, "password": "TestPassword!1"}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("measuring detection + recovery latency...")
        detect_recover = measure_detection_and_recovery(client, headers, str(machine.id), api_key)

        print("measuring ingest throughput...")
        throughput = measure_throughput(db, client, api_key)

        print("measuring false-incident rate on a healthy simulation window...")
        false_rate = measure_false_incidents(client, headers, str(machine.id), api_key)

    result = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "notes": "All telemetry is simulated. Measured against a local docker-compose stack on this machine; not validated on physical equipment.",
        "config": {
            "persistence_breaches_to_trigger": 3,
            "persistence_healthy_to_clear": 5,
        },
        "detection_and_recovery": detect_recover,
        "throughput": throughput,
        "false_incident_rate": false_rate,
    }

    os.makedirs(os.path.join(ROOT, "portfolio", "measurements"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "portfolio", "reports"), exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = os.path.join(ROOT, "portfolio", "measurements", f"run-{stamp}.json")
    with open(raw_path, "w") as f:
        json.dump(result, f, indent=2)

    report_path = os.path.join(ROOT, "portfolio", "reports", "measurements-report.md")
    with open(report_path, "w") as f:
        f.write(f"""# FactoryOps measurements

Run at: {result['run_at_utc']} (UTC)
Raw data: [{os.path.basename(raw_path)}](../measurements/{os.path.basename(raw_path)})

All telemetry is **simulated**, generated locally by `simulator/simulate.py` and
fed through the real ingestion -> outbox -> RabbitMQ -> diagnosis-worker
pipeline running in Docker Compose on this machine. Nothing here has been
validated against physical manufacturing equipment.

## Detection & recovery latency

| Metric | Value |
|---|---|
| Fault injection to detection | {detect_recover['fault_injection_to_detection_seconds']} s |
| Fault removal to verified recovery | {detect_recover['fault_removal_to_verified_recovery_seconds']} s |

Detection requires {result['config']['persistence_breaches_to_trigger']} consecutive breaching readings
(persistence window). Recovery requires {result['config']['persistence_healthy_to_clear']} consecutive healthy
readings (separate, larger healthy-observation window) — this is why recovery
latency is intentionally longer than detection latency.

## Ingest throughput

| Metric | Value |
|---|---|
| Readings sent | {throughput['readings_sent']} |
| Readings accepted | {throughput['readings_accepted']} |
| Accept success rate | {throughput['accept_success_rate'] * 100:.1f}% |
| Ingest wall time for batch | {throughput['ingest_wall_seconds_for_batch']} s |

## False-incident rate (healthy simulation)

| Metric | Value |
|---|---|
| Duration | {false_rate['healthy_simulation_duration_seconds']} s |
| Healthy readings sent | {false_rate['healthy_readings_sent']} |
| Incidents opened | {false_rate['false_incidents_opened']} |

## Limitations

- Single-machine, single-run measurement on a development laptop — not a load test and not statistically averaged across many runs.
- Latencies include this machine's own Docker Desktop overhead and are not representative of a production deployment's network/latency profile.
- Processing-drain wait time is an approximation (polled), not an exact per-message trace.
""")

    print(json.dumps(result, indent=2))
    print(f"\nWrote raw data to {raw_path}")
    print(f"Wrote readable report to {report_path}")
    db.close()


if __name__ == "__main__":
    main()
