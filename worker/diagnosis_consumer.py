"""Diagnosis worker: consumes ingested readings and runs the fault-detection rule engine.

Guarantees provided here:
  * Duplicate-safe processing — a `processed_messages` row keyed by the broker
    message-id is written in the SAME transaction as any state/incident change,
    so redelivery of an already-handled message is a pure no-op.
  * Defined out-of-order behavior — a reading older than the last one already
    folded into a machine/fault-type's state is stored but does not move that
    state machine (it cannot un-breach or un-clear a threshold retroactively).
  * One active incident per (machine, fault_type) — enforced by both the rule
    engine's state machine and a Postgres partial unique index as a backstop.
  * Bounded retries + dead-letter — a processing exception is retried via a
    TTL-requeue queue up to `max_delivery_attempts` times, then dead-lettered.
"""
import json
import logging
import time
from datetime import datetime, timezone

from prometheus_client import Counter, Histogram, start_http_server
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.db import SessionLocal
from app.knowledge import KNOWLEDGE
from app.models import FaultType, Incident, MachineFaultState, ProcessedMessage, Severity
from app.rules import MetricThreshold, evaluate
from rabbitmq import declare_topology, get_connection, publish_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s diagnosis-worker %(levelname)s %(message)s")
log = logging.getLogger("diagnosis-worker")

PROCESSED = Counter("factoryops_readings_processed_total", "Readings successfully processed")
DUPLICATES = Counter("factoryops_readings_duplicate_total", "Duplicate messages ignored")
FAILURES = Counter("factoryops_readings_failed_total", "Reading processing failures")
RETRIED = Counter("factoryops_readings_retried_total", "Messages republished to the retry queue")
DEAD_LETTERED = Counter("factoryops_readings_dead_lettered_total", "Messages sent to the dead-letter queue")
INCIDENTS_OPENED = Counter("factoryops_incidents_opened_total", "Incidents opened", ["fault_type"])
INCIDENTS_RESOLVED = Counter("factoryops_incidents_resolved_total", "Incidents resolved", ["fault_type"])
DETECTION_LATENCY = Histogram(
    "factoryops_detection_latency_seconds",
    "Time from the reading that first breached a threshold to incident creation",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30, 60),
)

METRICS = {
    FaultType.overheating: ("temperature_c", MetricThreshold(settings.temp_trigger_c, settings.temp_clear_c, "C")),
    FaultType.overload: ("current_a", MetricThreshold(settings.current_trigger_a, settings.current_clear_a, "A")),
    FaultType.vibration: ("vibration_mm_s", MetricThreshold(settings.vibration_trigger_mm_s, settings.vibration_clear_mm_s, "mm/s")),
}

SEVERITY = {
    FaultType.overheating: Severity.critical,
    FaultType.overload: Severity.critical,
    FaultType.vibration: Severity.warning,
    FaultType.missing_telemetry: Severity.warning,
}


def _get_or_create_state(db, machine_id, fault_type: FaultType) -> MachineFaultState:
    state = (
        db.query(MachineFaultState)
        .filter(MachineFaultState.machine_id == machine_id, MachineFaultState.fault_type == fault_type)
        .with_for_update()
        .one_or_none()
    )
    if state is None:
        state = MachineFaultState(machine_id=machine_id, fault_type=fault_type, state="healthy")
        db.add(state)
        db.flush()
    return state


def _open_incident(db, machine_id, factory_lookup, fault_type: FaultType, value: float, unit: str, threshold: MetricThreshold, breaches: int):
    factory_id = factory_lookup(machine_id)
    kb = KNOWLEDGE[fault_type]
    incident = Incident(
        factory_id=factory_id,
        machine_id=machine_id,
        fault_type=fault_type,
        severity=SEVERITY[fault_type],
        status="open",
        observations={"summary": kb["summary_template"].format(trigger=threshold.trigger, breaches=breaches, value=value)},
        evidence={
            "metric": fault_type.value,
            "unit": unit,
            "trigger_threshold": threshold.trigger,
            "clear_threshold": threshold.clear,
            "consecutive_breaches_required": breaches,
            "last_value": value,
            "note": "Evidence is derived from simulated telemetry thresholds, not a trained model.",
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
        return None
    INCIDENTS_OPENED.labels(fault_type=fault_type.value).inc()
    return incident


def _resolve_incident(db, machine_id, fault_type: FaultType):
    incident = (
        db.query(Incident)
        .filter(Incident.machine_id == machine_id, Incident.fault_type == fault_type, Incident.status == "open")
        .one_or_none()
    )
    if incident is None:
        return
    incident.status = "resolved"
    incident.resolved_at = datetime.now(timezone.utc)
    incident.recovery_verified = True
    INCIDENTS_RESOLVED.labels(fault_type=fault_type.value).inc()


def process_reading(db, payload: dict, factory_lookup) -> None:
    machine_id = payload["machine_id"]
    reading_ts = datetime.fromisoformat(payload["ts"])

    for fault_type, (field, threshold) in METRICS.items():
        value = payload[field]
        state = _get_or_create_state(db, machine_id, fault_type)

        if state.last_reading_ts is not None and reading_ts <= state.last_reading_ts:
            log.info("out-of-order reading for machine=%s fault=%s ignored for state advancement", machine_id, fault_type.value)
            continue

        result = evaluate(
            value=value,
            threshold=threshold,
            consecutive_breach=state.consecutive_breach,
            consecutive_healthy=state.consecutive_healthy,
            state=state.state,
            persistence_breaches_to_trigger=settings.persistence_breaches_to_trigger,
            persistence_healthy_to_clear=settings.persistence_healthy_to_clear,
        )
        state.consecutive_breach = result.consecutive_breach
        state.consecutive_healthy = result.consecutive_healthy
        state.state = result.state
        state.last_reading_ts = reading_ts

        if result.transitioned_to_active:
            _open_incident(db, machine_id, factory_lookup, fault_type, value, threshold.unit, threshold, settings.persistence_breaches_to_trigger)
        elif result.transitioned_to_healthy:
            _resolve_incident(db, machine_id, fault_type)

    # A reading arriving at all is a "healthy" signal for missing-telemetry recovery.
    mt_state = _get_or_create_state(db, machine_id, FaultType.missing_telemetry)
    if mt_state.state == "active":
        mt_state.consecutive_healthy += 1
        mt_state.consecutive_breach = 0
        if mt_state.consecutive_healthy >= settings.persistence_healthy_to_clear:
            mt_state.state = "healthy"
            _resolve_incident(db, machine_id, FaultType.missing_telemetry)
    mt_state.last_reading_ts = reading_ts


def handle_delivery(channel, method, properties, body: bytes, factory_lookup) -> None:
    message_id = properties.message_id or f"no-id-{time.time()}"
    headers = properties.headers or {}
    attempt = int(headers.get("x-attempt", 1))

    db = SessionLocal()
    try:
        already = db.query(ProcessedMessage).filter(ProcessedMessage.message_id == message_id).one_or_none()
        if already is not None:
            DUPLICATES.inc()
            channel.basic_ack(method.delivery_tag)
            return

        payload = json.loads(body)
        if payload.get("_poison"):
            raise ValueError("simulated poison message for dead-letter demonstration")

        process_reading(db, payload, factory_lookup)
        db.add(ProcessedMessage(message_id=message_id))
        db.commit()
        PROCESSED.inc()
        channel.basic_ack(method.delivery_tag)
    except Exception:
        db.rollback()
        log.exception("processing failed for message_id=%s attempt=%s", message_id, attempt)
        FAILURES.inc()
        if attempt < settings.max_delivery_attempts:
            publish_json(
                channel, exchange="", routing_key=settings.readings_retry_queue,
                message_id=message_id, body=json.loads(body), headers={**headers, "x-attempt": attempt + 1},
            )
            RETRIED.inc()
        else:
            publish_json(
                channel, exchange="", routing_key=settings.readings_dead_letter_queue,
                message_id=message_id, body=json.loads(body), headers={**headers, "x-final-attempt": attempt},
            )
            DEAD_LETTERED.inc()
        channel.basic_ack(method.delivery_tag)
    finally:
        db.close()


def main() -> None:
    from app.models import Machine

    def factory_lookup(machine_id):
        db = SessionLocal()
        try:
            return db.query(Machine).filter(Machine.id == machine_id).one().factory_id
        finally:
            db.close()

    start_http_server(9102)
    conn = get_connection()
    channel = conn.channel()
    declare_topology(channel)
    channel.basic_qos(prefetch_count=1)

    def _callback(ch, method, properties, body):
        handle_delivery(ch, method, properties, body, factory_lookup)

    channel.basic_consume(queue=settings.readings_queue, on_message_callback=_callback)
    log.info("diagnosis worker consuming from %s", settings.readings_queue)
    channel.start_consuming()


if __name__ == "__main__":
    main()
