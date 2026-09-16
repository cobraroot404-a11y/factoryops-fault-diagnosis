from datetime import timedelta

import pytest

from .helpers import get_open_incident, now_utc, send_reading, wait_until

# Bounded by missing_telemetry_seconds (default 30s) + check interval (default
# 10s) + the healthy-recovery window, so this test legitimately takes longer
# than the others.
pytestmark = pytest.mark.timeout(120)


def test_missing_telemetry_is_detected_and_recovers(client, isolated_world):
    headers = {"Authorization": f"Bearer {isolated_world['technician_token']}"}
    send_reading(client, isolated_world["machine_api_key"], now_utc())

    # Then go silent — no more readings — until the scheduled checker notices.
    incident = wait_until(
        lambda: get_open_incident(client, headers, isolated_world["machine_id"], "missing_telemetry"),
        timeout_seconds=75,
        interval_seconds=2,
    )
    assert incident["fault_type"] == "missing_telemetry"

    # Resume sending readings; recovery requires the same healthy-observation window.
    ts = now_utc()
    for i in range(6):
        send_reading(client, isolated_world["machine_api_key"], ts + timedelta(seconds=i))

    def resolved():
        resp = client.get("/incidents", headers=headers, params={"machine_id": isolated_world["machine_id"], "status": "resolved"})
        resp.raise_for_status()
        return next((i for i in resp.json() if i["fault_type"] == "missing_telemetry"), None)

    resolved_incident = wait_until(resolved, timeout_seconds=30)
    assert resolved_incident["recovery_verified"] is True
