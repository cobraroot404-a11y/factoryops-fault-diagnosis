from datetime import timedelta

import pytest

from .helpers import get_open_incident, now_utc, send_healthy_burst, send_reading, wait_until

pytestmark = pytest.mark.timeout(90)


def test_healthy_readings_create_no_incident(client, isolated_world):
    headers = {"Authorization": f"Bearer {isolated_world['technician_token']}"}
    send_healthy_burst(client, isolated_world["machine_api_key"], now_utc(), count=10, step_seconds=1)

    def check():
        resp = client.get("/incidents", headers=headers, params={"machine_id": isolated_world["machine_id"]})
        resp.raise_for_status()
        return resp.json() == []

    # Give the pipeline time to process everything, then assert it STAYS empty.
    import time
    time.sleep(4)
    assert check(), "healthy telemetry must never open an incident"


@pytest.mark.parametrize(
    "field,bad_value",
    [("temperature_c", 95.0), ("current_a", 22.0), ("vibration_mm_s", 9.0)],
)
def test_each_metric_fault_opens_expected_incident(client, isolated_world, field, bad_value):
    fault_type = {"temperature_c": "overheating", "current_a": "overload", "vibration_mm_s": "vibration"}[field]
    headers = {"Authorization": f"Bearer {isolated_world['technician_token']}"}
    ts = now_utc()
    for i in range(4):
        kwargs = {"temperature_c": 50.0, "current_a": 10.0, "vibration_mm_s": 2.0}
        kwargs[field] = bad_value
        send_reading(client, isolated_world["machine_api_key"], ts + timedelta(seconds=i), **kwargs)

    incident = wait_until(lambda: get_open_incident(client, headers, isolated_world["machine_id"], fault_type))
    assert incident["status"] == "open"
    assert incident["fault_type"] == fault_type
    assert len(incident["suspected_causes"]) > 0
    assert len(incident["checklist"]) > 0
    assert "confidence" not in str(incident["evidence"]).lower()


def test_hysteresis_band_noise_does_not_flap_an_incident(client, isolated_world):
    headers = {"Authorization": f"Bearer {isolated_world['technician_token']}"}
    ts = now_utc()
    # 80C is between clear(75) and trigger(85): noise here must never open an incident.
    for i in range(15):
        send_reading(client, isolated_world["machine_api_key"], ts + timedelta(seconds=i), temperature_c=80.0)

    import time
    time.sleep(4)
    assert get_open_incident(client, headers, isolated_world["machine_id"], "overheating") is None


def test_duplicate_idempotency_key_does_not_duplicate_incidents(client, isolated_world):
    headers = {"Authorization": f"Bearer {isolated_world['technician_token']}"}
    ts = now_utc()
    key = "fixed-duplicate-key"
    for i in range(4):
        r = send_reading(client, isolated_world["machine_api_key"], ts + timedelta(seconds=i), temperature_c=95.0, idempotency_key=f"{key}-{i}")
        assert r.status_code == 202
    # Re-send the exact same readings again (simulating network-retry redelivery).
    for i in range(4):
        r = send_reading(client, isolated_world["machine_api_key"], ts + timedelta(seconds=i), temperature_c=95.0, idempotency_key=f"{key}-{i}")
        assert r.json()["status"] == "duplicate_ignored"

    incident = wait_until(lambda: get_open_incident(client, headers, isolated_world["machine_id"], "overheating"))
    resp = client.get("/incidents", headers=headers, params={"machine_id": isolated_world["machine_id"]})
    matching = [i for i in resp.json() if i["fault_type"] == "overheating"]
    assert len(matching) == 1, "duplicate delivery must not create a second incident"
    assert incident["id"] == matching[0]["id"]


def test_out_of_order_reading_does_not_corrupt_state(client, isolated_world):
    headers = {"Authorization": f"Bearer {isolated_world['technician_token']}"}
    base = now_utc()
    # Breach 3 times in order to open the incident.
    for i in range(3):
        send_reading(client, isolated_world["machine_api_key"], base + timedelta(seconds=i), temperature_c=95.0)
    wait_until(lambda: get_open_incident(client, headers, isolated_world["machine_id"], "overheating"))

    # Now deliver a STALE healthy reading timestamped before the breach window.
    send_reading(client, isolated_world["machine_api_key"], base - timedelta(seconds=10), temperature_c=50.0)

    import time
    time.sleep(4)
    incident = get_open_incident(client, headers, isolated_world["machine_id"], "overheating")
    assert incident is not None, "a stale out-of-order healthy reading must not retroactively clear an incident"


def test_recovery_requires_full_healthy_observation_window(client, isolated_world):
    headers = {"Authorization": f"Bearer {isolated_world['technician_token']}"}
    base = now_utc()
    for i in range(3):
        send_reading(client, isolated_world["machine_api_key"], base + timedelta(seconds=i), temperature_c=95.0)
    wait_until(lambda: get_open_incident(client, headers, isolated_world["machine_id"], "overheating"))

    # Only 2 healthy readings (default requires 5) — must still be open.
    t = base + timedelta(seconds=10)
    for i in range(2):
        send_reading(client, isolated_world["machine_api_key"], t + timedelta(seconds=i), temperature_c=50.0)
    import time
    time.sleep(3)
    assert get_open_incident(client, headers, isolated_world["machine_id"], "overheating") is not None

    # Send the remaining healthy readings to complete the window.
    t = t + timedelta(seconds=5)
    for i in range(5):
        send_reading(client, isolated_world["machine_api_key"], t + timedelta(seconds=i), temperature_c=50.0)

    def resolved():
        resp = client.get("/incidents", headers=headers, params={"machine_id": isolated_world["machine_id"], "status": "resolved"})
        resp.raise_for_status()
        return next((i for i in resp.json() if i["fault_type"] == "overheating"), None)

    incident = wait_until(resolved)
    assert incident["recovery_verified"] is True
