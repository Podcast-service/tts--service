from confluent_kafka import Producer
import logging
import json
import time
from app.config import settings

logger = logging.getLogger(__name__)

_producer = None

def get_producer():
    global _producer
    if _producer is None:
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'tts-service',
        }
        _producer = Producer(conf)
    return _producer

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Message delivery failed: {err}")

def send_event(topic: str, key: str, event_data: dict):
    producer = get_producer()
    payload = json.dumps(event_data).encode('utf-8')

    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            producer.produce(
                topic,
                key=key,
                value=payload,
                callback=delivery_report
            )
            producer.poll(0)
            return
        except BufferError:
            logger.warning(
                "Kafka producer queue is full (attempt %s/%s), polling and retrying",
                attempt,
                max_attempts,
            )
            producer.poll(0.5)
            time.sleep(0.1)

    raise RuntimeError("Failed to enqueue Kafka event after retries: producer queue is full")