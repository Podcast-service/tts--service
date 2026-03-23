from app.celery_app import celery_app
from app.config import settings
from app.kafka_producer import send_event
from silero_tts.silero_tts import SileroTTS
import os
import time
import logging
import threading
import wave
import shutil

logger = logging.getLogger(__name__)

# Per-process storage for models (keyed by voice)
_model_local = threading.local()
_model_init_lock = threading.Lock()
_MODEL_LOCK_FILE = "/tmp/tts_model_init.lock"


def _is_corrupted_torch_archive_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "pytorchstreamreader failed reading zip archive" in message
        or "failed finding central directory" in message
    )


def _clear_torch_cache():
    torch_home = os.getenv("TORCH_HOME", os.path.expanduser("~/.cache/torch"))
    cache_paths = [
        torch_home,
        os.path.join(torch_home, "hub"),
        os.path.join(torch_home, "checkpoints"),
    ]

    for cache_path in cache_paths:
        if os.path.exists(cache_path):
            shutil.rmtree(cache_path, ignore_errors=True)
            logger.warning(f"Torch cache removed due to corrupted archive: {cache_path}")


def _acquire_model_init_file_lock(timeout_seconds: int = 120):
    start = time.time()
    while True:
        try:
            fd = os.open(_MODEL_LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("utf-8"))
            return fd
        except FileExistsError:
            if time.time() - start > timeout_seconds:
                raise TimeoutError("Timeout while waiting model init lock")
            time.sleep(0.5)


def _release_model_init_file_lock(fd: int):
    try:
        os.close(fd)
    finally:
        if os.path.exists(_MODEL_LOCK_FILE):
            os.remove(_MODEL_LOCK_FILE)


def _load_model_for_voice(voice: str):
    model_id = SileroTTS.get_latest_model(settings.SILERO_LANGUAGE)
    return SileroTTS(
        model_id=model_id,
        language=settings.SILERO_LANGUAGE,
        speaker=voice,
        sample_rate=48000,
        device='cpu'
    )


def _drop_cached_voice_model(voice: str):
    if hasattr(_model_local, 'models') and voice in _model_local.models:
        del _model_local.models[voice]
        logger.warning(f"Dropped cached TTS model for voice '{voice}'")

def get_tts_model(voice: str):
    """Returns SileroTTS model for the given voice, loads if needed."""
    if not hasattr(_model_local, 'models'):
        _model_local.models = {}
    if voice not in _model_local.models:
        with _model_init_lock:
            if voice in _model_local.models:
                return _model_local.models[voice]

            logger.info(f"Loading Silero TTS model for voice '{voice}'...")

            lock_fd = _acquire_model_init_file_lock()
            try:
                _model_local.models[voice] = _load_model_for_voice(voice)
            except Exception as model_error:
                if _is_corrupted_torch_archive_error(model_error):
                    logger.warning(
                        "Corrupted torch archive detected while loading model. "
                        "Clearing cache and retrying once..."
                    )
                    _clear_torch_cache()
                    _model_local.models[voice] = _load_model_for_voice(voice)
                else:
                    raise
            finally:
                _release_model_init_file_lock(lock_fd)

            logger.info(f"Silero TTS model for voice '{voice}' loaded.")
    return _model_local.models[voice]


def build_part_audio_path(parent_task_id: str, part_index: int) -> str:
    return os.path.join(settings.AUDIO_DIR, f"{parent_task_id}_part_{part_index}.wav")


def build_final_audio_path(task_id: str) -> str:
    return os.path.join(settings.AUDIO_DIR, f"{task_id}.wav")


def cleanup_audio_files(file_paths: list[str]):
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as cleanup_error:
            logger.warning(f"Failed to remove file '{file_path}': {cleanup_error}")


def merge_wav_files(input_paths: list[str], output_path: str):
    if not input_paths:
        raise ValueError("No audio parts to merge")

    expected_params = None

    with wave.open(output_path, 'wb') as destination:
        for input_path in input_paths:
            with wave.open(input_path, 'rb') as source:
                current_params = (
                    source.getnchannels(),
                    source.getsampwidth(),
                    source.getframerate(),
                    source.getcomptype(),
                    source.getcompname(),
                )

                if expected_params is None:
                    expected_params = current_params
                    destination.setnchannels(current_params[0])
                    destination.setsampwidth(current_params[1])
                    destination.setframerate(current_params[2])
                    destination.setcomptype(current_params[3], current_params[4])
                elif current_params != expected_params:
                    raise ValueError("Audio parts have incompatible WAV parameters")

                destination.writeframes(source.readframes(source.getnframes()))


def synthesize_part_to_path(text: str, voice: str, parent_task_id: str, part_index: int) -> str:
    audio_path = build_part_audio_path(parent_task_id, part_index)

    try:
        tts_model = get_tts_model(voice)
        tts_model.tts(text, audio_path)
    except Exception as error:
        if _is_corrupted_torch_archive_error(error):
            logger.warning(
                "Corrupted archive error during synthesis. "
                "Dropping cached model and clearing torch cache before retry."
            )
            _drop_cached_voice_model(voice)
            _clear_torch_cache()
        raise

    return audio_path


@celery_app.task(
    bind=True,
    name="generate_tts_part",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
    retry_jitter=True,
)
def generate_tts_part(self, text: str, voice: str, parent_task_id: str, part_index: int):
    return synthesize_part_to_path(text, voice, parent_task_id, part_index)

@celery_app.task(bind=True, name="generate_tts")
def generate_tts(self, items: list[dict]):
    task_id = self.request.id
    audio_path = build_final_audio_path(task_id)
    os.makedirs(settings.AUDIO_DIR, exist_ok=True)

    part_audio_paths = [build_part_audio_path(task_id, idx) for idx in range(len(items))]

    try:
        generated_part_paths = []
        for index, item in enumerate(items):
            part_path = synthesize_part_to_path(item["text"], item["voice"], task_id, index)
            generated_part_paths.append(part_path)

        merge_wav_files(generated_part_paths, audio_path)
        cleanup_audio_files(generated_part_paths)

        send_event(
            settings.KAFKA_TOPIC_COMPLETED,
            key=task_id,
            event_data={
                "task_id": task_id,
                "status": "completed",
                "items": items,
                "file_url": f"/audio/{task_id}.wav",
                "timestamp": time.time()
            }
        )
        logger.info(f"Task {task_id} completed, audio saved to {audio_path}")

    except Exception as e:
        cleanup_audio_files(part_audio_paths + [audio_path])

        logger.exception(f"Task {task_id} failed: {e}")
        send_event(
            settings.KAFKA_TOPIC_FAILED,
            key=task_id,
            event_data={
                "task_id": task_id,
                "status": "failed",
                "items": items,
                "error": str(e),
                "timestamp": time.time()
            }
        )
        raise