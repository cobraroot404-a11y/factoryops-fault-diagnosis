"""Demonstration + test: stop the diagnosis worker, show the queue backlog
grow, restore the worker, and confirm the backlog drains into exactly one
incident (no duplicates) once processing resumes. Requires a running stack
(scripts/start.sh) and docker on the PATH.
"""
import time
from datetime import timedelta

import pytest

from .conftest import compose, queue_message_count
from .helpers import get_open_incident, now_utc, send_reading, wait_until

pytestmark = pytest.mark.timeout(120)


def test_worker_stop_backlog_growth_and_safe_recovery(client, isolated_world):
    headers = {"Authorization": f"Bearer {isolated_world['technician_token']}"}

    print("\n[1/5] stopping diagnosis-worker...")
    compose("stop", "diagnosis-worker")
    time.sleep(2)

    print("[2/5] sending readings while the worker is down...")
    base = now_utc()
    for i in range(6):
        send_reading(client, isolated_world["machine_api_key"], base + timedelta(seconds=i), temperature_c=95.0)

    def backlog_present():
        return queue_message_count("readings.process") > 0

    wait_until(backlog_present, timeout_seconds=20)
    backlog = queue_message_count("readings.process")
    print(f"[3/5] backlog confirmed: {backlog} message(s) queued while worker was stopped")
    assert backlog > 0

    print("[4/5] restoring diagnosis-worker...")
    compose("start", "diagnosis-worker")

    incident = wait_until(lambda: get_open_incident(client, headers, isolated_world["machine_id"], "overheating"), timeout_seconds=30)
    print(f"[5/5] backlog drained safely, incident opened exactly once: {incident['id']}")

    resp = client.get("/incidents", headers=headers, params={"machine_id": isolated_world["machine_id"]})
    matches = [i for i in resp.json() if i["fault_type"] == "overheating"]
    assert len(matches) == 1, "restored worker must not create duplicate incidents while draining the backlog"
