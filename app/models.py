from pydantic import BaseModel, Field, ConfigDict, validator
from app.config import settings

class TTSPart(BaseModel):
    text: str
    voice: str

    @validator("voice")
    def validate_voice(cls, v):
        if v not in settings.ALLOWED_VOICES:
            raise ValueError(f"voice must be one of {settings.ALLOWED_VOICES}")
        return v


class TTSRequest(BaseModel):
    items: list[TTSPart] = Field(min_length=1)
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "text": "Привет, меня зовут Айдар.",
                        "voice": "aidar"
                    },
                    {
                        "text": "А меня зовут Ксения.",
                        "voice": "kseniya"
                    }
                ]
            }
        }
    )

class TaskResponse(BaseModel):
    task_id: str
    status: str = "processing"
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "9f6e53b4-3c45-4f2a-9ad8-7a1ed98d2b4e",
                "status": "processing"
            }
        }
    )