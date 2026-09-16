import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser, get_current_user, require_role
from app.models import Incident, IncidentStatus, Machine, Role, Ticket, TicketStatus
from app.schemas import TicketCreate, TicketOut

router = APIRouter(prefix="/tickets", tags=["tickets"])

CORRELATION_WINDOW = timedelta(hours=24)


def _correlate(db: Session, machine_id: uuid.UUID) -> Incident | None:
    """Link a ticket to the most relevant incident for its machine: prefer an open
    incident, otherwise the most recently resolved one within the correlation window."""
    now = datetime.now(timezone.utc)
    open_incident = (
        db.query(Incident)
        .filter(Incident.machine_id == machine_id, Incident.status == IncidentStatus.open)
        .order_by(Incident.opened_at.desc())
        .first()
    )
    if open_incident:
        return open_incident
    recent = (
        db.query(Incident)
        .filter(
            Incident.machine_id == machine_id,
            Incident.status == IncidentStatus.resolved,
            Incident.resolved_at >= now - CORRELATION_WINDOW,
        )
        .order_by(Incident.resolved_at.desc())
        .first()
    )
    return recent


def _to_out(db: Session, t: Ticket) -> TicketOut:
    machine = db.query(Machine).filter(Machine.id == t.machine_id).one()
    return TicketOut(
        id=t.id, machine_id=t.machine_id, machine_name=machine.name,
        symptoms=t.symptoms, error_code=t.error_code, status=t.status,
        linked_incident_id=t.linked_incident_id, created_at=t.created_at,
    )


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    body: TicketCreate,
    user: CurrentUser = Depends(require_role(Role.customer)),
    db: Session = Depends(get_db),
):
    machine = db.query(Machine).filter(Machine.id == body.machine_id).one_or_none()
    if machine is None or machine.factory_id != user.factory_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Machine not found")

    incident = _correlate(db, machine.id)
    ticket = Ticket(
        factory_id=user.factory_id,
        customer_id=user.id,
        machine_id=machine.id,
        symptoms=body.symptoms,
        error_code=body.error_code,
        status=TicketStatus.linked if incident else TicketStatus.open,
        linked_incident_id=incident.id if incident else None,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return _to_out(db, ticket)


@router.get("", response_model=list[TicketOut])
def list_tickets(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Ticket).filter(Ticket.factory_id == user.factory_id)
    if user.role == Role.customer:
        q = q.filter(Ticket.customer_id == user.id)
    rows = q.order_by(Ticket.created_at.desc()).all()
    return [_to_out(db, t) for t in rows]
