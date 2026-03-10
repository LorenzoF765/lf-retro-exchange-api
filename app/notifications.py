"""
Kafka notification publisher for the Retro Exchange API.

Provides a single public function, `publish_event(event_type, payload)`, which
serializes a structured event to JSON and sends it to the configured Kafka topic.
The KafkaProducer is lazily initialized on first use so importing this module
never blocks startup.  If Kafka is unavailable the error is logged and the API
continues normally (fail-open).

Coded by LF using copilot inline additions, Copilot added comments afterwards.
"""
import json
import logging
import os
from typing import Any, Dict

from kafka import KafkaProducer

logger = logging.getLogger(__name__)

# Environment-configurable bootstrap servers (comma-separated host:port pairs)
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
NOTIFICATIONS_TOPIC = os.getenv("NOTIFICATIONS_TOPIC", "notifications")

# Module-level producer — created once, reused across requests.
_producer: KafkaProducer | None = None


def _get_producer() -> KafkaProducer:
    """Return the module-level KafkaProducer, initializing it on first call.

    Raises KafkaError if the broker is unreachable on first initialization;
    subsequent calls after a failure will re-attempt initialization so that
    the producer recovers automatically if Kafka comes back online.
    """
    global _producer
    if _producer is not None:
        return _producer
    logger.info("Initializing Kafka producer → %s", KAFKA_BOOTSTRAP)
    # Raise on failure so the caller can catch and log; _producer stays None
    # and will be retried on the next call.
    _producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=5,
    )
    return _producer


def publish_event(event_type: str, payload: Dict[str, Any]) -> None:
    """Publish a structured event to the notifications Kafka topic.

    Args:
        event_type: Short identifier for the event, e.g. ``"offer.created"``.
        payload:    JSON-serializable dict with event-specific data.

    The function is intentionally fire-and-forget: if Kafka is unavailable the
    exception is logged and swallowed so callers are not affected.
    """
    event = {"type": event_type, "payload": payload}
    try:
        producer = _get_producer()
        producer.send(NOTIFICATIONS_TOPIC, event)
        producer.flush(timeout=5)
        logger.debug("Published %s → %s", event_type, payload)
    except Exception:
        # Don't let a Kafka outage impact the API response.
        logger.exception("Failed to publish event type=%s", event_type)
