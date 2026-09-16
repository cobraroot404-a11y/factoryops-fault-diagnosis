"""Integration test fixtures.

These tests exercise the REAL running stack (backend API + Postgres +
RabbitMQ + diagnosis worker + missing-telemetry checker) started by
`docker compose`. Run them with scripts/run-tests.sh, which points
DATABASE_URL/RABBITMQ_URL/BACKEND_BASE_URL at the published localhost ports.

Each test creates its own uniquely-named factory/users/machine so tests never
collide with each other or with the human-facing demo seed data.
"""
import os
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def db_session():
    from app.db import SessionLocal
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


@pytest.fixture
def isolated_world(db_session):
    """Creates: one factory, one customer, one technician, one machine.
    Returns a dict with tokens, machine id/api key, and factory id."""
    from app.models import Factory, Machine, Role, User
    from app.security import generate_machine_api_key, hash_machine_api_key, hash_password

    suffix = uuid.uuid4().hex[:8]
    factory = Factory(name=f"Test Factory {suffix}")
    db_session.add(factory)
    db_session.flush()

    password = "TestPassword!1"
    customer = User(
        factory_id=factory.id, email=f"customer-{suffix}@test.local", role=Role.customer,
        display_name="Test Customer", password_hash=hash_password(password),
    )
    technician = User(
        factory_id=factory.id, email=f"technician-{suffix}@test.local", role=Role.technician,
        display_name="Test Technician", password_hash=hash_password(password),
    )
    db_session.add_all([customer, technician])

    plaintext_key = generate_machine_api_key()
    machine = Machine(factory_id=factory.id, name=f"Test-Motor-{suffix}", api_key_hash=hash_machine_api_key(plaintext_key))
    db_session.add(machine)
    db_session.commit()

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        customer_token = c.post("/auth/login", json={"email": customer.email, "password": password}).json()["access_token"]
        technician_token = c.post("/auth/login", json={"email": technician.email, "password": password}).json()["access_token"]

    return {
        "factory_id": str(factory.id),
        "customer_token": customer_token,
        "technician_token": technician_token,
        "machine_id": str(machine.id),
        "machine_api_key": plaintext_key,
        "suffix": suffix,
    }


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
