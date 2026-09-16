from datetime import timedelta

import pytest

from .helpers import get_open_incident, now_utc, send_reading, wait_until

pytestmark = pytest.mark.timeout(60)


def test_ticket_correlates_to_open_incident_on_same_machine(client, isolated_world):
    tech_headers = {"Authorization": f"Bearer {isolated_world['technician_token']}"}
    cust_headers = {"Authorization": f"Bearer {isolated_world['customer_token']}"}

    ts = now_utc()
    for i in range(3):
        send_reading(client, isolated_world["machine_api_key"], ts + timedelta(seconds=i), current_a=22.0)
    incident = wait_until(lambda: get_open_incident(client, tech_headers, isolated_world["machine_id"], "overload"))

    resp = client.post(
        "/tickets", headers=cust_headers,
        json={"machine_id": isolated_world["machine_id"], "symptoms": "motor keeps stopping", "error_code": "E-104"},
    )
    assert resp.status_code == 201
    ticket = resp.json()
    assert ticket["status"] == "linked"
    assert ticket["linked_incident_id"] == incident["id"]


def test_ticket_without_a_relevant_incident_stays_unlinked(client, isolated_world):
    cust_headers = {"Authorization": f"Bearer {isolated_world['customer_token']}"}
    resp = client.post(
        "/tickets", headers=cust_headers,
        json={"machine_id": isolated_world["machine_id"], "symptoms": "just checking in, no problem"},
    )
    assert resp.status_code == 201
    ticket = resp.json()
    assert ticket["status"] == "open"
    assert ticket["linked_incident_id"] is None


def test_technician_cannot_create_a_ticket(client, isolated_world):
    tech_headers = {"Authorization": f"Bearer {isolated_world['technician_token']}"}
    resp = client.post(
        "/tickets", headers=tech_headers,
        json={"machine_id": isolated_world["machine_id"], "symptoms": "should be rejected"},
    )
    assert resp.status_code == 403
