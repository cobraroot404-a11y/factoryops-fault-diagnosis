import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser, get_current_user, require_role
from app.models import Incident, IncidentStatus, Machine, Role, Severity
from app.schemas import ChecklistUpdate, IncidentOut

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _to_out(db: Session, inc: Incident) -> IncidentOut:
    machine = db.query(Machine).filter(Machine.id == inc.machine_id).one()
    return IncidentOut(
        id=inc.id, machine_id=inc.machine_id, machine_name=machine.name,
        fault_type=inc.fault_type, severity=inc.severity, status=inc.status,
        opened_at=inc.opened_at, resolved_at=inc.resolved_at,
        observations=inc.observations, evidence=inc.evidence,
        suspected_causes=inc.suspected_causes, next_checks=inc.next_checks,
        checklist=inc.checklist, recovery_verified=inc.recovery_verified,
    )


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    severity: Severity | None = None,
    machine_id: uuid.UUID | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Incident).filter(Incident.factory_id == user.factory_id)
    if status_filter:
        q = q.filter(Incident.status == status_filter)
    if severity:
        q = q.filter(Incident.severity == severity)
    if machine_id:
        q = q.filter(Incident.machine_id == machine_id)
    rows = q.order_by(Incident.opened_at.desc()).all()
    return [_to_out(db, i) for i in rows]


def _get_owned_incident(db: Session, user: CurrentUser, incident_id: uuid.UUID) -> Incident:
    inc = db.query(Incident).filter(Incident.id == incident_id).one_or_none()
    if inc is None or inc.factory_id != user.factory_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")
    return inc


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inc = _get_owned_incident(db, user, incident_id)
    return _to_out(db, inc)


@router.post("/{incident_id}/checklist", response_model=IncidentOut)
def update_checklist(
    incident_id: uuid.UUID,
    body: ChecklistUpdate,
    user: CurrentUser = Depends(require_role(Role.technician)),
    db: Session = Depends(get_db),
):
    inc = _get_owned_incident(db, user, incident_id)
    checklist = list(inc.checklist)
    if body.step_index >= len(checklist):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid checklist step")
    checklist[body.step_index] = {**checklist[body.step_index], "done": body.done}
    inc.checklist = checklist
    db.commit()
    db.refresh(inc)
    return _to_out(db, inc)
