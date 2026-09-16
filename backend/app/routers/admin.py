import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser, require_role
from app.models import FaultInjection, Machine, Role
from app.schemas import FaultInjectionOut, FaultInjectionRequest

router = APIRouter(prefix="/admin/fault-injections", tags=["admin"])


def _to_out(db: Session, fi: FaultInjection) -> FaultInjectionOut:
    machine = db.query(Machine).filter(Machine.id == fi.machine_id).one()
    return FaultInjectionOut(
        id=fi.id, machine_id=fi.machine_id, machine_name=machine.name,
        fault_type=fi.fault_type, active=fi.active,
        injected_at=fi.injected_at, removed_at=fi.removed_at,
    )


@router.get("", response_model=list[FaultInjectionOut])
def list_active(user: CurrentUser = Depends(require_role(Role.technician)), db: Session = Depends(get_db)):
    rows = (
        db.query(FaultInjection)
        .join(Machine, Machine.id == FaultInjection.machine_id)
        .filter(Machine.factory_id == user.factory_id, FaultInjection.active == True)  # noqa: E712
        .all()
    )
    return [_to_out(db, r) for r in rows]


@router.post("", response_model=FaultInjectionOut, status_code=status.HTTP_201_CREATED)
def inject_fault(
    body: FaultInjectionRequest,
    user: CurrentUser = Depends(require_role(Role.technician)),
    db: Session = Depends(get_db),
):
    machine = db.query(Machine).filter(Machine.id == body.machine_id).one_or_none()
    if machine is None or machine.factory_id != user.factory_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Machine not found")

    existing = (
        db.query(FaultInjection)
        .filter(
            FaultInjection.machine_id == machine.id,
            FaultInjection.fault_type == body.fault_type,
            FaultInjection.active == True,  # noqa: E712
        )
        .one_or_none()
    )
    if existing:
        return _to_out(db, existing)

    fi = FaultInjection(machine_id=machine.id, fault_type=body.fault_type, injected_by=user.id, active=True)
    db.add(fi)
    db.commit()
    db.refresh(fi)
    return _to_out(db, fi)


@router.delete("/{injection_id}", response_model=FaultInjectionOut)
def remove_fault(
    injection_id: int,
    user: CurrentUser = Depends(require_role(Role.technician)),
    db: Session = Depends(get_db),
):
    fi = (
        db.query(FaultInjection)
        .join(Machine, Machine.id == FaultInjection.machine_id)
        .filter(FaultInjection.id == injection_id, Machine.factory_id == user.factory_id)
        .one_or_none()
    )
    if fi is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fault injection not found")
    fi.active = False
    fi.removed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(fi)
    return _to_out(db, fi)
