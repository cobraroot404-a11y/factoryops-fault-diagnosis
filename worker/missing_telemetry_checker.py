"""Scheduled missing-telemetry checker.

Runs on a fixed interval (independent of the reading pipeline, since the whole
point is to notice the ABSENCE of readings) and opens a missing_telemetry
incident for any machine whose last_seen_at is older than the configured
threshold. Recovery is handled by the diagnosis worker: once fresh readings
resume, it counts consecutive "healthy" arrivals and resolves the incident
after the same configurable healthy-observation window used by every other
fault type.
"""
import logging
import time
from datetime import datetime, timezone

from prometheus_client import Counter, start_http_server
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db import SessionLocal
from app.knowledge import KNOWLEDGE
from app.models import FaultType, Incident, Machine, MachineFaultState, Severity

logging.basicConfig(level=logging.INFO, format="%(asctime)s missing-telemetry-checker %(levelname)s %(message)s")
log = logging.getLogger("missing-telemetry-checker")

INCIDENTS_OPENED = Counter("factoryops_missing_telemetry_incidents_total", "Missing-telemetry incidents opened")


def check_once() -> int:
    db = SessionLocal()
    opened = 0
    try:
        now = datetime.now(timezone.utc)
        machines = db.query(Machine).all()
        for m in machines:
            if m.last_seen_at is None:
                continue
            age = (now - m.last_seen_at).total_seconds()
            if age <= settings.missing_telemetry_seconds:
                continue

            already_open = (
                db.query(Incident)
                .filter(Incident.machine_id == m.id, Incident.fault_type == FaultType.missing_telemetry, Incident.status == "open")
                .first()
            )
            if already_open:
                continue

            kb = KNOWLEDGE[FaultType.missing_telemetry]
            incident = Incident(
                factory_id=m.factory_id,
                machine_id=m.id,
                fault_type=FaultType.missing_telemetry,
                severity=Severity.warning,
                status="open",
                observations={"summary": kb["summary_template"].format(trigger=settings.missing_telemetry_seconds, value=f"{age:.0f}s ago")},
                evidence={
                    "metric": "seconds_since_last_reading",
                    "trigger_threshold_seconds": settings.missing_telemetry_seconds,
                    "last_seen_at": m.last_seen_at.isoformat(),
                    "note": "Evidence is derived from a simulated telemetry gap, not a trained model.",
                },
                suspected_causes=kb["suspected_causes"],
                next_checks=kb["next_checks"],
                checklist=[{"step": s, "done": False} for s in kb["checklist"]],
            )
            db.add(incident)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                continue

            state = (
                db.query(MachineFaultState)
                .filter(MachineFaultState.machine_id == m.id, MachineFaultState.fault_type == FaultType.missing_telemetry)
                .one_or_none()
            )
            if state is None:
                state = MachineFaultState(machine_id=m.id, fault_type=FaultType.missing_telemetry)
                db.add(state)
            state.state = "active"
            state.consecutive_healthy = 0

            db.commit()
            INCIDENTS_OPENED.inc()
            opened += 1
            log.info("opened missing_telemetry incident for machine=%s (silent for %.0fs)", m.id, age)
        return opened
    finally:
        db.close()


def main() -> None:
    start_http_server(9103)
    log.info("missing-telemetry checker running every %ss, threshold %ss", settings.missing_telemetry_check_interval_seconds, settings.missing_telemetry_seconds)
    while True:
        try:
            check_once()
        except Exception:
            log.exception("check iteration failed")
        time.sleep(settings.missing_telemetry_check_interval_seconds)


if __name__ == "__main__":
    main()
