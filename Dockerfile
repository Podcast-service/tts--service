FROM python:3.10-slim

# Устанавливаем Git (необходимо для клонирования репозитория silero-models, если бы мы его использовали)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./app /app/app

# Запускаем от root, чтобы иметь права на запись конфигурационных файлов Silero
# (для продакшена нужно будет решить иначе, но для тестирования сойдёт)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]