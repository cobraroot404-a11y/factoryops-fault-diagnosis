import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Float, ForeignKey, DateTime, Boolean, Integer, Text,
    UniqueConstraint, Index, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def uid() -> uuid.UUID:
    return uuid.uuid4()


class Role(str, enum.Enum):
    customer = "customer"
    technician = "technician"


class FaultType(str, enum.Enum):
    overheating = "overheating"
    overload = "overload"
    vibration = "vibration"
    missing_telemetry = "missing_telemetry"


class IncidentStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class Severity(str, enum.Enum):
    warning = "warning"
    critical = "critical"


class TicketStatus(str, enum.Enum):
    open = "open"
    linked = "linked"
    closed = "closed"


class FaultState(str, enum.Enum):
    healthy = "healthy"
    suspect = "suspect"
    active = "active"
    recovering = "recovering"


class Factory(Base):
    __tablename__ = "factories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="factory")
    machines: Mapped[list["Machine"]] = relationship(back_populates="factory")


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    factory: Mapped["Factory"] = relationship(back_populates="users")


class Machine(Base):
    __tablename__ = "machines"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    machine_type: Mapped[str] = mapped_column(String(40), default="industrial_motor")
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    factory: Mapped["Factory"] = relationship(back_populates="machines")

    __table_args__ = (UniqueConstraint("factory_id", "name", name="uq_machine_factory_name"),)


class Reading(Base):
    __tablename__ = "readings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    current_a: Mapped[float] = mapped_column(Float, nullable=False)
    vibration_mm_s: Mapped[float] = mapped_column(Float, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("machine_id", "idempotency_key", name="uq_reading_machine_idempotency"),
        Index("ix_readings_machine_ts", "machine_id", "ts"),
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (Index("ix_outbox_unpublished", "published_at"),)


class MachineFaultState(Base):
    __tablename__ = "machine_fault_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("machines.id"), nullable=False)
    fault_type: Mapped[FaultType] = mapped_column(String(30), nullable=False)
    state: Mapped[FaultState] = mapped_column(String(20), default=FaultState.healthy)
    consecutive_breach: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_healthy: Mapped[int] = mapped_column(Integer, default=0)
    last_reading_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("machine_id", "fault_type", name="uq_fault_state_machine_type"),)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"), nullable=False, index=True)
    machine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    fault_type: Mapped[FaultType] = mapped_column(String(30), nullable=False)
    severity: Mapped[Severity] = mapped_column(String(20), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(String(20), default=IncidentStatus.open, index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observations: Mapped[dict] = mapped_column(JSONB, default=dict)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    suspected_causes: Mapped[list] = mapped_column(JSONB, default=list)
    next_checks: Mapped[list] = mapped_column(JSONB, default=list)
    checklist: Mapped[list] = mapped_column(JSONB, default=list)
    recovery_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index(
            "uq_open_incident_machine_fault",
            "machine_id", "fault_type",
            unique=True,
            postgresql_where=(status == "open"),
        ),
    )


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    factory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("factories.id"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    machine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("machines.id"), nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[TicketStatus] = mapped_column(String(20), default=TicketStatus.open)
    linked_incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FaultInjection(Base):
    __tablename__ = "fault_injections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("machines.id"), nullable=False)
    fault_type: Mapped[FaultType] = mapped_column(String(30), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    injected_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    injected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "uq_active_injection_machine_fault",
            "machine_id", "fault_type",
            unique=True,
            postgresql_where=(active == True),  # noqa: E712
        ),
    )


class ProcessedMessage(Base):
    """Consumer-side dedup safety net, keyed by producer-assigned message id."""
    __tablename__ = "processed_messages"
    message_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
