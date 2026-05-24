from app.celery_app import celery_app
from app.config import settings
from app.kafka_producer import send_event
from app.s3_uploader import upload_audio_file
from silero_tts.silero_tts import SileroTTS
import os
import time
import logging
import threading
import wave
import shutil

logger = logging.getLogger(__name__)

# Per-process singleton model to avoid loading duplicated weights per voice.
_tts_model = None
_model_init_lock = threading.Lock()
_model_use_lock = threading.Lock()
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


def _load_model():
    model_id = SileroTTS.get_latest_model(settings.SILERO_LANGUAGE)
    return SileroTTS(
        model_id=model_id,
        language=settings.SILERO_LANGUAGE,
        speaker=settings.SILERO_DEFAULT_VOICE,
        sample_rate=48000,
        device='cpu'
    )


def _drop_cached_model():
    global _tts_model
    with _model_init_lock:
        _tts_model = None
    logger.warning("Dropped cached TTS model")

def get_tts_model():
    """Returns singleton SileroTTS model for current worker process."""
    global _tts_model
    if _tts_model is None:
        with _model_init_lock:
            if _tts_model is not None:
                return _tts_model

            logger.info("Loading Silero TTS model...")

            lock_fd = _acquire_model_init_file_lock()
            try:
                _tts_model = _load_model()
            except Exception as model_error:
                if _is_corrupted_torch_archive_error(model_error):
                    logger.warning(
                        "Corrupted torch archive detected while loading model. "
                        "Clearing cache and retrying once..."
                    )
                    _clear_torch_cache()
                    _tts_model = _load_model()
                else:
                    raise
            finally:
                _release_model_init_file_lock(lock_fd)

            logger.info("Silero TTS model loaded.")
    return _tts_model


def build_part_audio_path(id_podcast: str, part_index: int) -> str:
    return os.path.join(settings.AUDIO_DIR, f"{id_podcast}_part_{part_index}.wav")


def build_final_audio_path(id_podcast: str) -> str:
    return os.path.join(settings.AUDIO_DIR, f"{id_podcast}.wav")


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

                while True:
                    # Stream by chunks to avoid loading long segments into RAM at once.
                    chunk = source.readframes(8192)
                    if not chunk:
                        break
                    destination.writeframes(chunk)


def synthesize_part_to_path(text: str, voice: str, id_podcast: str, part_index: int) -> str:
    audio_path = build_part_audio_path(id_podcast, part_index)

    try:
        tts_model = get_tts_model()
        with _model_use_lock:
            tts_model.speaker = voice
            tts_model.tts(text, audio_path)
    except Exception as error:
        if _is_corrupted_torch_archive_error(error):
            logger.warning(
                "Corrupted archive error during synthesis. "
                "Dropping cached model and clearing torch cache before retry."
            )
            _drop_cached_model()
            _clear_torch_cache()
        raise

    return audio_path


@celery_app.task(name="generate_tts")
def generate_tts(id_podcast: str, text_items: list[dict]):
    audio_path = build_final_audio_path(id_podcast)
    os.makedirs(settings.AUDIO_DIR, exist_ok=True)

    part_audio_paths = [build_part_audio_path(id_podcast, idx) for idx in range(len(text_items))]

    try:
        generated_part_paths = []
        for index, item in enumerate(text_items):
            part_path = synthesize_part_to_path(item["text"], item["voice"], id_podcast, index)
            generated_part_paths.append(part_path)

        merge_wav_files(generated_part_paths, audio_path)
        cleanup_audio_files(generated_part_paths)

        audio_size_file = os.path.getsize(audio_path)
        audio_url_file = upload_audio_file(audio_path, id_podcast)
        cleanup_audio_files([audio_path])

        send_event(
            settings.KAFKA_TOPIC_MEDIA_UPLOADED,
            key=id_podcast,
            event_data={
                "id_podcast": id_podcast,
                "audio_url_file": audio_url_file,
                "audio_size_file": audio_size_file,
                "timestamp": time.time(),
                "add.transcipt": False,
            },
        )
        logger.info(f"Podcast {id_podcast} uploaded to {audio_url_file}")

    except Exception as e:
        cleanup_audio_files(part_audio_paths + [audio_path])

        logger.exception(f"Podcast {id_podcast} failed: {e}")
        send_event(
            settings.KAFKA_TOPIC_FAILED,
            key=id_podcast,
            event_data={
                "id_podcast": id_podcast,
                "text": text_items,
                "error": str(e),
                "timestamp": time.time(),
            },
        )
        raise
    