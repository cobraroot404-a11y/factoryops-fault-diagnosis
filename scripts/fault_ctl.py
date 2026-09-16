#!/usr/bin/env python3
"""Authorized demo fault-injection CLI. Logs in as a technician for the
target machine's factory (using the seeded demo credentials) and calls the
fault-injection API. Usage:

  python scripts/fault_ctl.py inject "Northgate Assembly/Motor-1" overheating
  python scripts/fault_ctl.py remove "Northgate Assembly/Motor-1" overheating
  python scripts/fault_ctl.py list
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://localhost:8000")
CRED_PATH = os.path.join(os.path.dirname(__file__), "..", "infra", "compose", "seed-output", "demo-credentials.json")


def call(method: str, path: str, token: str | None = None, body: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        raise


def technician_token(factory_name: str) -> str:
    with open(CRED_PATH) as f:
        creds = json.load(f)
    match = next((c for c in creds if c["role"] == "technician" and c["factory"] == factory_name), None)
    if match is None:
        raise SystemExit(f"No seeded technician found for factory '{factory_name}'. Run scripts/seed.sh first.")
    res = call("POST", "/auth/login", body={"email": match["email"], "password": match["password"]})
    return res["access_token"]


def find_machine(token: str, factory_name: str, machine_name: str) -> str:
    machines = call("GET", "/machines", token=token)
    match = next((m for m in machines if m["name"] == machine_name), None)
    if match is None:
        raise SystemExit(f"Machine '{machine_name}' not found in factory '{factory_name}'.")
    return match["id"]


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    action = sys.argv[1]

    if action == "list":
        with open(CRED_PATH) as f:
            creds = json.load(f)
        factories = sorted({c["factory"] for c in creds})
        for factory in factories:
            token = technician_token(factory)
            active = call("GET", "/admin/fault-injections", token=token)
            print(f"{factory}:")
            for a in active:
                print(f"  - {a['machine_name']}: {a['fault_type']} (injected {a['injected_at']}, id={a['id']})")
        return

    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(1)

    _, action, machine_ref, fault_type = sys.argv
    factory_name, machine_name = machine_ref.split("/", 1)
    token = technician_token(factory_name)
    machine_id = find_machine(token, factory_name, machine_name)

    if action == "inject":
        res = call("POST", "/admin/fault-injections", token=token, body={"machine_id": machine_id, "fault_type": fault_type})
        print(f"Injected {fault_type} on {machine_ref} (injection id={res['id']})")
    elif action == "remove":
        active = call("GET", "/admin/fault-injections", token=token)
        match = next((a for a in active if a["machine_id"] == machine_id and a["fault_type"] == fault_type), None)
        if match is None:
            raise SystemExit(f"No active '{fault_type}' injection found on {machine_ref}.")
        call("DELETE", f"/admin/fault-injections/{match['id']}", token=token)
        print(f"Removed {fault_type} from {machine_ref}")
    else:
        print(__doc__)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
