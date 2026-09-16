import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models import Incident, IncidentStatus, Machine, Reading
from app.schemas import MachineOut, ReadingOut

router = APIRouter(prefix="/machines", tags=["machines"])


def _machine_health(db: Session, machine: Machine) -> str:
    has_open_incident = (
        db.query(Incident)
        .filter(Incident.machine_id == machine.id, Incident.status == IncidentStatus.open)
        .first()
        is not None
    )
    if has_open_incident:
        return "fault"
    if machine.last_seen_at is None:
        return "unknown"
    age = (datetime.now(timezone.utc) - machine.last_seen_at).total_seconds()
    if age > settings.missing_telemetry_seconds:
        return "missing"
    return "healthy"


@router.get("", response_model=list[MachineOut])
def list_machines(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    machines = db.query(Machine).filter(Machine.factory_id == user.factory_id).order_by(Machine.name).all()
    out = []
    for m in machines:
        out.append(MachineOut(
            id=m.id, name=m.name, machine_type=m.machine_type,
            last_seen_at=m.last_seen_at, health=_machine_health(db, m),
        ))
    return out


def _get_owned_machine(db: Session, user: CurrentUser, machine_id: uuid.UUID) -> Machine:
    machine = db.query(Machine).filter(Machine.id == machine_id).one_or_none()
    if machine is None or machine.factory_id != user.factory_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Machine not found")
    return machine


@router.get("/{machine_id}/readings", response_model=list[ReadingOut])
def machine_readings(
    machine_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_machine(db, user, machine_id)
    rows = (
        db.query(Reading)
        .filter(Reading.machine_id == machine_id)
        .order_by(Reading.ts.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


@router.get("/{machine_id}/readings/latest", response_model=ReadingOut | None)
def latest_reading(
    machine_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_machine(db, user, machine_id)
    row = (
        db.query(Reading)
        .filter(Reading.machine_id == machine_id)
        .order_by(Reading.ts.desc())
        .first()
    )
    return row
