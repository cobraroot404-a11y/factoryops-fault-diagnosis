import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models import FaultType, IncidentStatus, Role, Severity, TicketStatus


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    factory_id: uuid.UUID
    display_name: str


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: Role
    factory_id: uuid.UUID
    factory_name: str
    display_name: str


class MachineOut(BaseModel):
    id: uuid.UUID
    name: str
    machine_type: str
    last_seen_at: datetime | None
    health: str

    class Config:
        from_attributes = True


class ReadingOut(BaseModel):
    ts: datetime
    temperature_c: float
    current_a: float
    vibration_mm_s: float

    class Config:
        from_attributes = True


class ReadingIn(BaseModel):
    ts: datetime
    temperature_c: float = Field(ge=-50, le=300)
    current_a: float = Field(ge=0, le=1000)
    vibration_mm_s: float = Field(ge=0, le=200)
    idempotency_key: str = Field(min_length=1, max_length=80)


class TicketCreate(BaseModel):
    machine_id: uuid.UUID
    symptoms: str = Field(min_length=3, max_length=2000)
    error_code: str | None = Field(default=None, max_length=40)

    @field_validator("symptoms")
    @classmethod
    def strip_symptoms(cls, v: str) -> str:
        return v.strip()


class TicketOut(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    machine_name: str
    symptoms: str
    error_code: str | None
    status: TicketStatus
    linked_incident_id: uuid.UUID | None
    created_at: datetime


class IncidentOut(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    machine_name: str
    fault_type: FaultType
    severity: Severity
    status: IncidentStatus
    opened_at: datetime
    resolved_at: datetime | None
    observations: dict
    evidence: dict
    suspected_causes: list
    next_checks: list
    checklist: list
    recovery_verified: bool


class ChecklistUpdate(BaseModel):
    step_index: int = Field(ge=0)
    done: bool


class FaultInjectionRequest(BaseModel):
    machine_id: uuid.UUID
    fault_type: FaultType


class FaultInjectionOut(BaseModel):
    id: int
    machine_id: uuid.UUID
    machine_name: str
    fault_type: FaultType
    active: bool
    injected_at: datetime
    removed_at: datetime | None
