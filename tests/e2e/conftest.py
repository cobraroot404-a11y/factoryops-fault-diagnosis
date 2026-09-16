"""Fixtures for the e2e demonstration tests, which run on the HOST against a
live docker-compose stack's published ports (they need to run `docker compose
stop/start` themselves, which only works from outside any container)."""
import os
import subprocess
import sys
import uuid

import httpx
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))

BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://localhost:8000")
RABBITMQ_MGMT_URL = os.environ.get("RABBITMQ_MGMT_URL", "http://localhost:15672")
RABBITMQ_USER = os.environ.get("RABBITMQ_DEFAULT_USER", "factoryops")
RABBITMQ_PASS = os.environ.get("RABBITMQ_DEFAULT_PASS", "changeme-local-only")
COMPOSE_FILE = os.path.join(ROOT, "infra", "compose", "docker-compose.yml")
ENV_FILE = os.path.join(ROOT, ".env")


def compose(*args: str) -> None:
    subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "--env-file", ENV_FILE, *args], check=True, cwd=ROOT)


def queue_message_count(queue: str) -> int:
    resp = httpx.get(f"{RABBITMQ_MGMT_URL}/api/queues/%2F/{queue}", auth=(RABBITMQ_USER, RABBITMQ_PASS), timeout=10)
    resp.raise_for_status()
    return resp.json().get("messages", 0)


@pytest.fixture
def isolated_world():
    from app.db import SessionLocal
    from app.models import Factory, Machine, Role, User
    from app.security import generate_machine_api_key, hash_machine_api_key, hash_password

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    factory = Factory(name=f"E2E Factory {suffix}")
    db.add(factory)
    db.flush()
    password = "TestPassword!1"
    technician = User(
        factory_id=factory.id, email=f"technician-e2e-{suffix}@test.local", role=Role.technician,
        display_name="E2E Technician", password_hash=hash_password(password),
    )
    db.add(technician)
    plaintext_key = generate_machine_api_key()
    machine = Machine(factory_id=factory.id, name=f"E2E-Motor-{suffix}", api_key_hash=hash_machine_api_key(plaintext_key))
    db.add(machine)
    db.commit()

    with httpx.Client(base_url=BACKEND_BASE_URL, timeout=10.0) as c:
        token = c.post("/auth/login", json={"email": technician.email, "password": password}).json()["access_token"]

    yield {"machine_id": str(machine.id), "machine_api_key": plaintext_key, "technician_token": token}
    db.close()


@pytest.fixture
def client():
    with httpx.Client(base_url=BACKEND_BASE_URL, timeout=10.0) as c:
        yield c
