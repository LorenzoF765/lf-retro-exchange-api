# Kafka consumer and email sender for notification events. Coded by LF using copilot
# inline additions; Copilot added comments afterwards.
"""
Kafka consumer that sends email notifications via an SMTP server (Ethereal).

This process subscribes to a `notifications` topic and, for supported events,
sends an email to the appropriate recipient. SMTP connection and Kafka
bootstrap address are configured via environment variables.

Run as: python -m app.email_worker
"""
import os
import json
import logging
import time
from email.message import EmailMessage
import smtplib
from kafka import KafkaConsumer

logger = logging.getLogger("email_worker")
logging.basicConfig(level=os.getenv("EMAIL_WORKER_LOG_LEVEL", "INFO"))

# Kafka and topic configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
NOTIFICATIONS_TOPIC = os.getenv("NOTIFICATIONS_TOPIC", "notifications")
KAFKA_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "email_worker_group")

# SMTP / Ethereal configuration (set these from the environment)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.ethereal.email")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")  # Ethereal user
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

# From address for outgoing mail
FROM_ADDRESS = os.getenv("EMAIL_FROM", "no-reply@example.com")


def send_email(to_email: str, subject: str, body: str) -> None:
    """Send a simple text email using configured SMTP settings."""
    msg = EmailMessage()
    msg["From"] = FROM_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if SMTP_USE_TLS:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
                smtp.starttls()
                if SMTP_USER and SMTP_PASS:
                    smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
                if SMTP_USER and SMTP_PASS:
                    smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
        logger.info("Sent email to %s subject=%s", to_email, subject)
    except Exception:
        logger.exception("Failed to send email to %s", to_email)


def handle_event(event: dict) -> None:
    """Dispatch supported notification event types into emails."""
    event_type = event.get("type")
    payload = event.get("payload", {})

    if event_type == "user.registered":
        # payload expected: { "user_id": int, "email": str, "name": str }
        to = payload.get("email")
        subject = "Welcome to Retro Video Game Exchange"
        body = f"Hi {payload.get('name', '')},\n\nThanks for registering. Welcome!"
        if to:
            send_email(to, subject, body)

    elif event_type == "offer.created":
        # payload expected: { "offer_id": int, "to_email": str, "from_name": str, "requested_game": str }
        to = payload.get("to_email")
        subject = "You have a new trade offer"
        body = (
            f"Hi,\n\n{payload.get('from_name')} has offered a trade for your game "
            f"\"{payload.get('requested_game')}\". Offer id: {payload.get('offer_id')}.\n\n"
            "Visit the app to review the offer."
        )
        if to:
            send_email(to, subject, body)

    elif event_type == "offer.decided":
        # payload expected: { "offer_id": int, "offerer_email": str, "status": str }
        to = payload.get("offerer_email")
        subject = f"Your offer was {payload.get('status')}"
        body = f"Hi,\n\nYour offer (id {payload.get('offer_id')}) was {payload.get('status')}."
        if to:
            send_email(to, subject, body)

    else:
        logger.debug("Unhandled event type: %s", event_type)


def main():
    """Main consumer loop."""
    logger.info("Starting email_worker, connecting to Kafka %s topic %s", KAFKA_BOOTSTRAP, NOTIFICATIONS_TOPIC)
    # Create consumer with retry/backoff so worker doesn't crash if broker is not
    # available immediately on container start.
    consumer = None

    while True:
        # Attempt to create the Kafka consumer, retrying with exponential backoff
        # until the broker becomes available.
        if consumer is None:
            max_attempts = int(os.getenv("KAFKA_CONNECT_RETRIES", "0"))
            # If max_attempts == 0, retry indefinitely
            attempt = 0
            delay = float(os.getenv("KAFKA_CONNECT_DELAY", "1"))
            while True:
                try:
                    consumer = KafkaConsumer(
                        NOTIFICATIONS_TOPIC,
                        bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
                        group_id=KAFKA_GROUP,
                        auto_offset_reset="earliest",
                        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                        enable_auto_commit=True,
                        consumer_timeout_ms=1000,
                    )
                    logger.info("Connected to Kafka broker(s) %s", KAFKA_BOOTSTRAP)
                    break
                except Exception:
                    attempt += 1
                    if max_attempts and attempt >= max_attempts:
                        logger.exception("Failed to connect to Kafka after %s attempts, exiting", attempt)
                        raise
                    sleep_time = min(delay * (2 ** (attempt - 1)), 60)
                    logger.warning("Kafka not available yet, retrying in %.1fs (attempt %s)", sleep_time, attempt)
                    time.sleep(sleep_time)

        try:
            for message in consumer:
                event = message.value
                logger.info("Received event %s", event.get("type"))
                try:
                    handle_event(event)
                except Exception:
                    logger.exception("Error handling event: %s", event)
            # Sleep-loop so worker can be responsive to container stops
            time.sleep(1)
        except Exception:
            logger.exception("Kafka consumer error; will recreate consumer and retry in 5s")
            try:
                if consumer is not None:
                    consumer.close()
            except Exception:
                pass
            consumer = None
            time.sleep(5)


if __name__ == "__main__":
    main()