from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_machine
from app.models import FaultInjection, Machine, Reading
from app.outbox import enqueue_event
from app.schemas import ReadingIn

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/active-faults")
def active_faults(machine: Machine = Depends(get_current_machine), db: Session = Depends(get_db)):
    """Polled by the simulator so demo fault injection can alter this machine's simulated output."""
    rows = (
        db.query(FaultInjection)
        .filter(FaultInjection.machine_id == machine.id, FaultInjection.active == True)  # noqa: E712
        .all()
    )
    return {"active_fault_types": [r.fault_type.value if hasattr(r.fault_type, "value") else r.fault_type for r in rows]}


@router.post("/readings", status_code=status.HTTP_202_ACCEPTED)
def ingest_reading(
    body: ReadingIn,
    machine: Machine = Depends(get_current_machine),
    db: Session = Depends(get_db),
):
    reading = Reading(
        machine_id=machine.id,
        ts=body.ts,
        temperature_c=body.temperature_c,
        current_a=body.current_a,
        vibration_mm_s=body.vibration_mm_s,
        idempotency_key=body.idempotency_key,
    )
    db.add(reading)
    try:
        db.flush()
    except IntegrityError:
        # Duplicate delivery of the same (machine, idempotency_key): accept idempotently, no re-publish.
        db.rollback()
        return {"status": "duplicate_ignored"}

    enqueue_event(
        db,
        event_type="reading.ingested",
        aggregate_id=str(machine.id),
        payload={
            "reading_id": reading.id,
            "machine_id": str(machine.id),
            "ts": body.ts.isoformat(),
            "temperature_c": body.temperature_c,
            "current_a": body.current_a,
            "vibration_mm_s": body.vibration_mm_s,
            "idempotency_key": body.idempotency_key,
        },
    )
    if machine.last_seen_at is None or body.ts > machine.last_seen_at:
        machine.last_seen_at = body.ts
    db.commit()
    return {"status": "accepted", "reading_id": reading.id}
