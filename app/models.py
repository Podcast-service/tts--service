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
    id_podcast: str = Field(min_length=1)
    text: list[TTSPart] = Field(min_length=1)
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id_podcast": "9f6e53b4-3c45-4f2a-9ad8-7a1ed98d2b4e",
                "text": [
                    {"text": "Привет, меня зовут Айдар.", "voice": "aidar"},
                    {"text": "А меня зовут Ксения.", "voice": "kseniya"},
                ],
            }
        }
    )


class TaskResponse(BaseModel):
    id_podcast: str
    status: str = "processing"
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id_podcast": "9f6e53b4-3c45-4f2a-9ad8-7a1ed98d2b4e",
                "status": "processing",
            }
        }
    )
