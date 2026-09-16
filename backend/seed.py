"""Idempotent local demo seed: two factories (for isolation testing), one
customer + one technician per factory, and simulated motors per factory.

Writes plaintext machine API keys to infra/compose/seed-output/machine-keys.json
(gitignored — consumed by the simulator) and demo login credentials to
infra/compose/seed-output/demo-credentials.json (gitignored — for local use only).
Safe to re-run: existing rows are left untouched.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.db import SessionLocal  # noqa: E402
from app.models import Factory, Machine, Role, User  # noqa: E402
from app.security import generate_machine_api_key, hash_machine_api_key, hash_password  # noqa: E402

OUTPUT_DIR = os.environ.get("SEED_OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "..", "infra", "compose", "seed-output"))
DEMO_PASSWORD = os.environ.get("SEED_DEMO_PASSWORD", "FactoryOps!Demo1")

PLAN = [
    {
        "factory": "Northgate Assembly",
        "machines": ["Motor-1", "Motor-2", "Motor-3"],
        "customer_email": "customer@northgate.factoryops.local",
        "technician_email": "technician@northgate.factoryops.local",
    },
    {
        "factory": "Rivermill Fabrication",
        "machines": ["Motor-A", "Motor-B"],
        "customer_email": "customer@rivermill.factoryops.local",
        "technician_email": "technician@rivermill.factoryops.local",
    },
]


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    db = SessionLocal()
    machine_keys = []
    credentials = []
    try:
        for entry in PLAN:
            factory = db.query(Factory).filter(Factory.name == entry["factory"]).one_or_none()
            if factory is None:
                factory = Factory(name=entry["factory"])
                db.add(factory)
                db.flush()
                print(f"created factory {factory.name}")

            for role, email in [(Role.customer, entry["customer_email"]), (Role.technician, entry["technician_email"])]:
                user = db.query(User).filter(User.email == email).one_or_none()
                if user is None:
                    user = User(
                        factory_id=factory.id, email=email, role=role,
                        display_name=f"{role.value.title()} ({factory.name})",
                        password_hash=hash_password(DEMO_PASSWORD),
                    )
                    db.add(user)
                    print(f"created {role.value} user {email}")
                credentials.append({"email": email, "password": DEMO_PASSWORD, "role": role.value, "factory": factory.name})

            for machine_name in entry["machines"]:
                machine = (
                    db.query(Machine)
                    .filter(Machine.factory_id == factory.id, Machine.name == machine_name)
                    .one_or_none()
                )
                if machine is None:
                    plaintext_key = generate_machine_api_key()
                    machine = Machine(factory_id=factory.id, name=machine_name, api_key_hash=hash_machine_api_key(plaintext_key))
                    db.add(machine)
                    print(f"created machine {machine_name} in {factory.name}")
                else:
                    plaintext_key = None

                if plaintext_key:
                    machine_keys.append({"name": f"{factory.name}/{machine_name}", "factory": factory.name, "api_key": plaintext_key})

            db.commit()

        if machine_keys:
            path = os.path.join(OUTPUT_DIR, "machine-keys.json")
            existing = {"machines": []}
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    existing = json.load(f)
            existing["machines"].extend(machine_keys)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            print(f"wrote {len(machine_keys)} new machine key(s) to {path}")

        cred_path = os.path.join(OUTPUT_DIR, "demo-credentials.json")
        with open(cred_path, "w", encoding="utf-8") as f:
            json.dump(credentials, f, indent=2)
        print(f"wrote demo credentials to {cred_path} (local only, gitignored)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
