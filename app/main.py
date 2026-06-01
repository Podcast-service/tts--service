from fastapi import FastAPI, Body
from app.models import TTSRequest, TaskResponse
from app.celery_app import celery_app
from app.config import settings
from app.kafka_producer import send_event, iso_now
import os

app = FastAPI(title="TTS Service", version="1.0.0")

@app.on_event("startup")
def startup_event():
    from app.kafka_producer import get_producer
    get_producer()
    os.makedirs(settings.AUDIO_DIR, exist_ok=True)


@app.post(
    "/api/tts/generate",
    response_model=TaskResponse,
    status_code=202,
    responses={
        202: {
            "description": "Task accepted",
            "content": {
                "application/json": {
                    "example": {
                        "id_podcast": "9f6e53b4-3c45-4f2a-9ad8-7a1ed98d2b4e",
                        "status": "processing",
                    }
                }
            },
        }
    },
)
async def generate_tts(
    request: TTSRequest = Body(
        ...,
        examples={
            "multi_voice": {
                "summary": "Multiple segments with different voices",
                "value": {
                    "id_podcast": "9f6e53b4-3c45-4f2a-9ad8-7a1ed98d2b4e",
                    "text": [
                        {"text": "Hello! This is the first segment with Aidar voice.", "voice": "aidar"},
                        {"text": "And this is the second segment with another voice.", "voice": "kseniya"},
                    ],
                },
            }
        },
    )
):
    """
    Accepts a podcast id and a list of text/voice segments,
    enqueues a TTS task and returns immediately.
    """
    text_items = [item.model_dump() for item in request.text]

    send_event(
        settings.KAFKA_TOPIC_START,
        key=request.id_podcast,
        event_data={
            "podcast_id": request.id_podcast,
            "content": text_items,
            "timestamp": iso_now(),
        },
    )

    celery_app.send_task(
        "generate_tts",
        args=[request.id_podcast, text_items],
        task_id=request.id_podcast,
    )

    return TaskResponse(id_podcast=request.id_podcast)
