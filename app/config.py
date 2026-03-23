import os

class Settings:
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TOPIC_REQUESTS = os.getenv("KAFKA_TOPIC_REQUESTS", "tts.requests")
    KAFKA_TOPIC_COMPLETED = os.getenv("KAFKA_TOPIC_COMPLETED", "tts.completed")
    KAFKA_TOPIC_FAILED = os.getenv("KAFKA_TOPIC_FAILED", "tts.failed")
    AUDIO_DIR = os.getenv("AUDIO_DIR", "/app/audio")
    ALLOWED_VOICES = {"aidar", "baya", "kseniya", "xenia", "eugene"}
    SILERO_LANGUAGE = "ru"

settings = Settings()