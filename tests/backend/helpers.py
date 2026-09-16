import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx


def send_reading(
    client: httpx.Client,
    api_key: str,
    ts: datetime,
    temperature_c: float = 50.0,
    current_a: float = 10.0,
    vibration_mm_s: float = 2.0,
    idempotency_key: str | None = None,
) -> httpx.Response:
    return client.post(
        "/telemetry/readings",
        headers={"X-API-Key": api_key},
        json={
            "ts": ts.isoformat(),
            "temperature_c": temperature_c,
            "current_a": current_a,
            "vibration_mm_s": vibration_mm_s,
            "idempotency_key": idempotency_key or str(uuid.uuid4()),
        },
    )


def send_healthy_burst(client: httpx.Client, api_key: str, start: datetime, count: int, step_seconds: float = 1.0) -> datetime:
    ts = start
    for _ in range(count):
        send_reading(client, api_key, ts)
        ts += timedelta(seconds=step_seconds)
    return ts


def wait_until(predicate, timeout_seconds: float = 30.0, interval_seconds: float = 0.5):
    deadline = time.monotonic() + timeout_seconds
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval_seconds)
    raise TimeoutError(f"condition not met within {timeout_seconds}s (last result: {last!r})")


def get_open_incident(client: httpx.Client, headers: dict, machine_id: str, fault_type: str):
    resp = client.get("/incidents", headers=headers, params={"status": "open", "machine_id": machine_id})
    resp.raise_for_status()
    matches = [i for i in resp.json() if i["fault_type"] == fault_type]
    return matches[0] if matches else None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
