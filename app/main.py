from fastapi import FastAPI, HTTPException, Body
from app.models import TTSRequest, TaskResponse
from app.celery_app import celery_app
from app.config import settings
from app.kafka_producer import send_event
import time
import uuid

app = FastAPI(title="TTS Service", version="1.0.0")

@app.on_event("startup")
def startup_event():
    from app.kafka_producer import get_producer
    get_producer()
    import os
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
                        "task_id": "9f6e53b4-3c45-4f2a-9ad8-7a1ed98d2b4e",
                        "status": "processing"
                    }
                }
            }
        }
    }
)
async def generate_tts(
    request: TTSRequest = Body(
        ...,
        examples={
            "multi_voice": {
                "summary": "Multiple segments with different voices",
                "value": {
                    "items": [
                        {
                            "text": "Hello! This is the first segment with Aidar voice.",
                            "voice": "aidar"
                        },
                        {
                            "text": "And this is the second segment with another voice.",
                            "voice": "kseniya"
                        }
                    ]
                }
            }
        }
    )
):
    """
    Accepts multiple text/voice items, puts task in queue and returns task ID.
    """
    task_id = str(uuid.uuid4())
    request_items = [item.model_dump() for item in request.items]

    send_event(
        settings.KAFKA_TOPIC_REQUESTS,
        key=task_id,
        event_data={
            "task_id": task_id,
            "status": "requested",
            "items": request_items,
            "timestamp": time.time()
        }
    )

    celery_app.send_task(
        "generate_tts",
        args=[request_items],
        task_id=task_id
    )

    return TaskResponse(task_id=task_id)

@app.get("/api/tts/status/{task_id}")
async def get_status(task_id: str):
    """
    Optional: get task execution status.
    """
    result = celery_app.AsyncResult(task_id)
    if result.state == "PENDING":
        return {"task_id": task_id, "status": "pending"}
    elif result.state == "SUCCESS":
        return {"task_id": task_id, "status": "completed"}
    elif result.state == "FAILURE":
        return {"task_id": task_id, "status": "failed", "error": str(result.info)}
    else:
        return {"task_id": task_id, "status": result.state.lower()}

from fastapi.staticfiles import StaticFiles
import os
if os.path.exists(settings.AUDIO_DIR):
    app.mount("/audio", StaticFiles(directory=settings.AUDIO_DIR), name="audio")