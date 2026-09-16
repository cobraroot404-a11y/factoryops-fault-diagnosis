import pytest

pytestmark = pytest.mark.timeout(60)


def test_customer_cannot_see_another_factorys_machine(client, isolated_world, db_session):
    """Seed a second, unrelated factory+machine, and confirm world A's users
    cannot reach it — this is the factory-isolation test the spec asks for."""
    from app.models import Factory, Machine
    from app.security import generate_machine_api_key, hash_machine_api_key
    import uuid

    other_factory = Factory(name=f"Other Factory {uuid.uuid4().hex[:8]}")
    db_session.add(other_factory)
    db_session.flush()
    other_machine = Machine(
        factory_id=other_factory.id, name="Other-Motor",
        api_key_hash=hash_machine_api_key(generate_machine_api_key()),
    )
    db_session.add(other_machine)
    db_session.commit()

    headers = {"Authorization": f"Bearer {isolated_world['customer_token']}"}
    resp = client.get(f"/machines/{other_machine.id}/readings/latest", headers=headers)
    assert resp.status_code == 404

    machines_resp = client.get("/machines", headers=headers)
    ids = [m["id"] for m in machines_resp.json()]
    assert str(other_machine.id) not in ids


def test_missing_auth_header_is_rejected(client, isolated_world):
    resp = client.get("/machines")
    assert resp.status_code == 401


def test_invalid_credentials_are_rejected(client, isolated_world):
    resp = client.post("/auth/login", json={"email": "nobody@nowhere.test", "password": "wrong"})
    assert resp.status_code == 401


def test_invalid_reading_payload_is_rejected(client, isolated_world):
    resp = client.post(
        "/telemetry/readings",
        headers={"X-API-Key": isolated_world["machine_api_key"]},
        json={"ts": "not-a-date", "temperature_c": 50, "current_a": 10, "vibration_mm_s": 2, "idempotency_key": "x"},
    )
    assert resp.status_code == 422


def test_reading_with_wrong_api_key_is_rejected(client, isolated_world):
    resp = client.post(
        "/telemetry/readings",
        headers={"X-API-Key": "not-a-real-key"},
        json={"ts": "2026-01-01T00:00:00Z", "temperature_c": 50, "current_a": 10, "vibration_mm_s": 2, "idempotency_key": "x"},
    )
    assert resp.status_code == 401


def test_customer_cannot_use_fault_injection_endpoints(client, isolated_world):
    headers = {"Authorization": f"Bearer {isolated_world['customer_token']}"}
    resp = client.post("/admin/fault-injections", headers=headers, json={"machine_id": isolated_world["machine_id"], "fault_type": "overheating"})
    assert resp.status_code == 403
