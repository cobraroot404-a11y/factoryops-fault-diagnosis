"""Demonstration + test: publish a message the diagnosis worker can never
process successfully (a controlled 'poison' message) directly onto the
processing queue, and confirm it reaches the dead-letter queue after exactly
`max_delivery_attempts` bounded retries — not retried forever, not silently
dropped.
"""
import json
import os
import sys
import time
import uuid

import pika
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from app.config import settings  # noqa: E402

from .conftest import RABBITMQ_PASS, RABBITMQ_USER, queue_message_count  # noqa: E402

pytestmark = pytest.mark.timeout(60)


def test_poison_message_reaches_dead_letter_queue_after_bounded_retries():
    rabbitmq_host_url = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@localhost:5672/"
    params = pika.URLParameters(rabbitmq_host_url)
    conn = pika.BlockingConnection(params)
    channel = conn.channel()
    channel.confirm_delivery()

    channel.exchange_declare(exchange=settings.telemetry_exchange, exchange_type="direct", durable=True)
    channel.queue_declare(queue=settings.readings_queue, durable=True)
    channel.queue_bind(queue=settings.readings_queue, exchange=settings.telemetry_exchange, routing_key="reading")

    message_id = f"poison-{uuid.uuid4()}"
    before = queue_message_count(settings.readings_dead_letter_queue)

    channel.basic_publish(
        exchange=settings.telemetry_exchange,
        routing_key="reading",
        body=json.dumps({"_poison": True, "machine_id": str(uuid.uuid4())}).encode(),
        properties=pika.BasicProperties(message_id=message_id, delivery_mode=2, headers={"x-attempt": 1}),
    )
    conn.close()

    # Bounded: max_delivery_attempts retries, each delayed by retry_delay_ms.
    max_wait = (settings.max_delivery_attempts * (settings.retry_delay_ms / 1000.0)) + 15
    deadline = time.monotonic() + max_wait
    after = before
    while time.monotonic() < deadline:
        after = queue_message_count(settings.readings_dead_letter_queue)
        if after > before:
            break
        time.sleep(1)

    assert after > before, f"expected the poison message in {settings.readings_dead_letter_queue} within {max_wait:.0f}s"
