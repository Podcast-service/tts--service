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

Три топика, ключ сообщения = `id_podcast`.

### `tts.start` — задача принята

```
{
  "id_podcast" 
  "text"
  "speakers_count"
  "timestamp"
}
```

### `media.uploaded` — аудио готово и залито в S3

```
{
  "id_podcast"
  "audio_url_file"
  "audio_size_file"
  "timestamp"
  "add.transcipt" 
}
```

### `tts.failed` 

```
{
  "id_podcast"
  "text"
  "error"
  "timestamp"
}
```