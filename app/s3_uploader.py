import boto3
from botocore.config import Config
from app.config import settings

_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        kwargs = {
            "aws_access_key_id": settings.S3_ACCESS_KEY or None,
            "aws_secret_access_key": settings.S3_SECRET_KEY or None,
            "region_name": settings.S3_REGION,
            "config": Config(signature_version="s3v4"),
        }
        if settings.S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        _s3_client = boto3.client("s3", **kwargs)
    return _s3_client


def build_audio_key(id_podcast: str) -> str:
    prefix = settings.S3_AUDIO_KEY_PREFIX.strip("/")
    filename = f"{id_podcast}.wav"
    return f"{prefix}/{filename}" if prefix else filename


def build_public_url(key: str) -> str:
    if settings.S3_PUBLIC_URL_BASE:
        return f"{settings.S3_PUBLIC_URL_BASE.rstrip('/')}/{key}"
    if settings.S3_ENDPOINT_URL:
        return f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{settings.S3_BUCKET}/{key}"
    return f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/{key}"


def upload_audio_file(local_path: str, id_podcast: str) -> str:
    key = build_audio_key(id_podcast)
    client = get_s3_client()
    client.upload_file(
        local_path,
        settings.S3_BUCKET,
        key,
        ExtraArgs={"ContentType": "audio/wav"},
    )
    return build_public_url(key)
