from sqlalchemy.orm import Session

from app.models import OutboxEvent


def enqueue_event(db: Session, event_type: str, aggregate_id: str, payload: dict) -> None:
    """Write an outbox row in the SAME transaction as the business write.

    A separate relay process polls unpublished rows and delivers them to RabbitMQ,
    so an accepted reading can never be silently lost even if the broker is down
    at the moment it was ingested (transactional outbox pattern).
    """
    db.add(OutboxEvent(event_type=event_type, aggregate_id=aggregate_id, payload=payload))
