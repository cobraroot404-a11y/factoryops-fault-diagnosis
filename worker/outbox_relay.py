"""Transactional-outbox relay.

The API commits (reading, outbox_event) atomically in one DB transaction, so an
accepted reading is durable even if RabbitMQ is unreachable at that instant. This
process is the only thing that talks to RabbitMQ on the write path: it polls
unpublished outbox rows and delivers them, marking them published only after a
broker publisher-confirm succeeds. If the broker is down, rows simply accumulate
in the outbox table and are delivered once it comes back — nothing is lost.
"""
import logging
import time
from datetime import datetime, timezone

from prometheus_client import Counter, start_http_server
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import OutboxEvent
from rabbitmq import declare_topology, get_connection, publish_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s outbox-relay %(levelname)s %(message)s")
log = logging.getLogger("outbox-relay")

RELAYED = Counter("factoryops_outbox_relayed_total", "Outbox events relayed to RabbitMQ")
POLL_INTERVAL_SECONDS = 1.0
BATCH_SIZE = 50


def relay_once(channel) -> int:
    db = SessionLocal()
    try:
        rows = (
            db.execute(
                select(OutboxEvent)
                .where(OutboxEvent.published_at.is_(None))
                .order_by(OutboxEvent.id)
                .limit(BATCH_SIZE)
            )
            .scalars()
            .all()
        )
        for row in rows:
            publish_json(
                channel,
                exchange=settings.telemetry_exchange,
                routing_key="reading",
                message_id=f"outbox-{row.id}",
                body=row.payload,
                headers={"x-attempt": 1, "event_type": row.event_type},
            )
            row.published_at = datetime.now(timezone.utc)
            row.attempts += 1
            db.add(row)
            db.commit()
            RELAYED.inc()
        return len(rows)
    finally:
        db.close()


def main() -> None:
    start_http_server(9101)
    conn = get_connection()
    channel = conn.channel()
    channel.confirm_delivery()
    declare_topology(channel)
    log.info("outbox relay started, polling every %.1fs", POLL_INTERVAL_SECONDS)
    while True:
        try:
            n = relay_once(channel)
            if n == 0:
                time.sleep(POLL_INTERVAL_SECONDS)
        except Exception:
            log.exception("relay iteration failed, reconnecting after backoff")
            time.sleep(2)
            try:
                conn = get_connection()
                channel = conn.channel()
                channel.confirm_delivery()
                declare_topology(channel)
            except Exception:
                log.exception("reconnect failed")


if __name__ == "__main__":
    main()
