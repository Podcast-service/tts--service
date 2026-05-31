# TTS Service

Асинхронный микросервис синтеза речи на базе [Silero TTS]. Принимает текст с разметкой по голосам, генерирует `.wav`, заливает в S3 и сообщает о результате через Kafka.

## Быстрый старт

### 1. Заполнить `.env`


### 2. Поднять docker

```
docker compose up --build
```

Первая сборка занимает 3–5 мин (PyTorch CPU + предзагрузка модели Silero в образ). Последующие старты — секунды.

### 3. Открыть Swagger

http://localhost:8000/docs

## API

### `POST /api/tts/generate`


**Body:**

```
{
  "id_podcast": "ep-001",
  "text": [
    { "text": "Привет, меня зовут Айдар.", "voice": "aidar" },
    { "text": "А меня зовут Ксения.",      "voice": "kseniya" }
  ]
}
```

**Ответ (202):**

```
{ "id_podcast": "ep-001", "status": "processing" }
```

## Kafka события

Ключ сообщения = `id_podcast`.

### `tts.start` — задача принята

```
{
  "podcast_id"
  "content"
  "timestamp"
}
```

При успешной генерации шлются два события: `media` и `media.upload`.

### `media` — аудио готово и залито в S3

```
{
  "event"
  "type"
  "object_id"
  "url"
  "size"
  "content_type"
  "need_subtitle"
  "uploaded_at"
}
```

### `media.upload` — аудио готово и залито в S3

```
{
  "object_type"
  "object_id"
  "event"
  "audio_url_file"
  "timestamp"
}
```

### `tts.failed` — ошибка генерации/загрузки

```
{
  "object_type"
  "object_id"
  "event"
  "error"
  "timestamp"
}
```