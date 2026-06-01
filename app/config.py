import os

class Settings:
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TOPIC_START = os.getenv("KAFKA_TOPIC_START", "tts.start")
    KAFKA_TOPIC_FAILED = os.getenv("KAFKA_TOPIC_FAILED", "tts.failed")
    KAFKA_TOPIC_MEDIA_UPLOADED = os.getenv("KAFKA_TOPIC_MEDIA_UPLOADED", "media")
    KAFKA_TOPIC_MEDIA_UPLOAD = os.getenv("KAFKA_TOPIC_MEDIA_UPLOAD", "media.upload")
    MEDIA_OBJECT_TYPE = os.getenv("MEDIA_OBJECT_TYPE", "podcast_file")
    MEDIA_OBJECT_TYPE_URL = os.getenv("MEDIA_OBJECT_TYPE_URL", "podcast_file_url")
    AUDIO_DIR = os.getenv("AUDIO_DIR", "/app/audio")
    ALLOWED_VOICES = {"aidar", "baya", "kseniya", "xenia", "eugene"}
    SILERO_LANGUAGE = "ru"
    SILERO_DEFAULT_VOICE = os.getenv("SILERO_DEFAULT_VOICE", "aidar")
    TTS_DEVICE = os.getenv("TTS_DEVICE", "cpu")

    CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
    CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "20"))
    CELERY_WORKER_MAX_MEMORY_PER_CHILD = int(os.getenv("CELERY_WORKER_MAX_MEMORY_PER_CHILD", "900000"))
    CELERY_RESULT_EXPIRES_SECONDS = int(os.getenv("CELERY_RESULT_EXPIRES_SECONDS", "3600"))

    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    S3_BUCKET = os.getenv("S3_BUCKET", "tts-audio")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
    S3_AUDIO_KEY_PREFIX = os.getenv("S3_AUDIO_KEY_PREFIX", "")
    S3_PUBLIC_URL_BASE = os.getenv("S3_PUBLIC_URL_BASE", "")

settings = Settings()
