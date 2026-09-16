import json

import pika

from app.config import settings


def get_connection() -> pika.BlockingConnection:
    params = pika.URLParameters(settings.rabbitmq_url)
    return pika.BlockingConnection(params)


def declare_topology(channel: pika.adapters.blocking_connection.BlockingChannel) -> None:
    """Main processing queue + a TTL-based retry queue (bounded retries) + a final DLQ.

    Retry pattern (no plugins required): a failed message is republished to
    `readings.retry`, which has a message TTL and a dead-letter-exchange pointing
    back at the default exchange with routing key = the main queue name. When the
    TTL expires, RabbitMQ automatically redelivers it to `readings.process`. After
    `max_delivery_attempts`, the message is instead published straight to the
    final `readings.dead-letter` queue for human inspection.
    """
    channel.exchange_declare(exchange=settings.telemetry_exchange, exchange_type="direct", durable=True)

    channel.queue_declare(queue=settings.readings_queue, durable=True)
    channel.queue_bind(queue=settings.readings_queue, exchange=settings.telemetry_exchange, routing_key="reading")

    channel.queue_declare(
        queue=settings.readings_retry_queue,
        durable=True,
        arguments={
            "x-message-ttl": settings.retry_delay_ms,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": settings.readings_queue,
        },
    )

    channel.queue_declare(queue=settings.readings_dead_letter_queue, durable=True)


def publish_json(channel, exchange: str, routing_key: str, message_id: str, body: dict, headers: dict | None = None) -> None:
    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=json.dumps(body).encode(),
        properties=pika.BasicProperties(
            message_id=message_id,
            content_type="application/json",
            delivery_mode=2,
            headers=headers or {},
        ),
    )
