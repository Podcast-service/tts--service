FROM python:3.10-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --index-url https://download.pytorch.org/whl/cpu \
        torch==2.2.2 torchaudio==2.2.2 \
    && pip install -r requirements.txt

# Pre-download Silero model and config at build time so containers start instantly
# and rebuilds don't re-fetch ~50MB on first request.
RUN python -c "from silero_tts.silero_tts import SileroTTS; \
SileroTTS(model_id=SileroTTS.get_latest_model('ru'), language='ru', speaker='aidar', sample_rate=48000, device='cpu')"

COPY ./app /app/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
