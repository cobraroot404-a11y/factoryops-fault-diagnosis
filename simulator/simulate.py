"""Simulated industrial-motor telemetry generator.

ALL data produced by this process is synthetic. It is used to exercise the
diagnosis pipeline without any physical hardware. Nothing here has been
validated against real manufacturing equipment.

Each configured machine has a healthy baseline (with small random noise) for
temperature, current draw, and vibration. Every tick it polls the backend for
which faults (if any) an operator has injected for that machine via the
authorized demo fault-injection controls, and ramps the relevant signal toward
an out-of-range value while the fault is active. A "missing_telemetry"
injection simply pauses sending for that machine.
"""
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone

import httpx

CONFIG_PATH = os.environ.get("SIMULATOR_CONFIG_PATH", "/config/machine-keys.json")
BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://backend:8000")
INTERVAL_SECONDS = float(os.environ.get("SIMULATE_INTERVAL_SECONDS", "2"))

HEALTHY = {"temperature_c": (45.0, 55.0), "current_a": (8.0, 12.0), "vibration_mm_s": (1.0, 2.5)}
FAULT_TARGET = {"overheating": ("temperature_c", 95.0), "overload": ("current_a", 22.0), "vibration": ("vibration_mm_s", 9.0)}
RAMP_STEP = {"temperature_c": 4.0, "current_a": 1.5, "vibration_mm_s": 0.8}
RECOVER_STEP = {"temperature_c": 3.0, "current_a": 1.2, "vibration_mm_s": 0.6}


class MachineSim:
    def __init__(self, name: str, api_key: str, base_url: str):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.value = {k: random.uniform(*v) for k, v in HEALTHY.items()}
        self.client = httpx.Client(base_url=base_url, headers={"X-API-Key": api_key}, timeout=5.0)

    def active_faults(self) -> list[str]:
        try:
            r = self.client.get("/telemetry/active-faults")
            r.raise_for_status()
            return r.json()["active_fault_types"]
        except Exception as e:
            print(f"[{self.name}] failed to poll active faults: {e}", file=sys.stderr)
            return []

    def step(self, active: list[str]) -> dict | None:
        if "missing_telemetry" in active:
            return None  # simulate a silent/offline machine

        for field, (lo, hi) in HEALTHY.items():
            fault_here = next((f for f, (ff, _) in FAULT_TARGET.items() if ff == field and f in active), None)
            if fault_here:
                _, target = FAULT_TARGET[fault_here]
                step = RAMP_STEP[field]
                self.value[field] += min(step, abs(target - self.value[field])) * (1 if target > self.value[field] else -1)
            else:
                mid = (lo + hi) / 2
                step = RECOVER_STEP[field]
                if abs(self.value[field] - mid) > step:
                    self.value[field] += step if mid > self.value[field] else -step
                self.value[field] += random.uniform(-0.3, 0.3)
                self.value[field] = max(0.0, self.value[field])

        return {k: round(v, 2) for k, v in self.value.items()}

    def send(self, reading: dict) -> None:
        body = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": str(uuid.uuid4()),
            **reading,
        }
        try:
            r = self.client.post("/telemetry/readings", json=body)
            if r.status_code >= 400:
                print(f"[{self.name}] ingest rejected: {r.status_code} {r.text}", file=sys.stderr)
        except Exception as e:
            print(f"[{self.name}] ingest failed: {e}", file=sys.stderr)


def load_machines() -> list[MachineSim]:
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    return [MachineSim(m["name"], m["api_key"], m.get("base_url", BASE_URL)) for m in cfg["machines"]]


def main() -> None:
    machines = load_machines()
    print(f"simulator started for {len(machines)} machine(s), interval={INTERVAL_SECONDS}s (SIMULATED DATA ONLY)")
    tick = 0
    while True:
        for m in machines:
            active = m.active_faults() if tick % 3 == 0 else getattr(m, "_last_active", [])
            m._last_active = active
            reading = m.step(active)
            if reading is not None:
                m.send(reading)
            else:
                print(f"[{m.name}] silent (missing_telemetry fault injected)")
        tick += 1
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
