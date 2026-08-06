# Jade Bɔngɔ́ — image tout-en-un (API + interfaces)
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    JADE_DB_PATH=/data/jade.db

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY frontend ./frontend

RUN mkdir -p /data
EXPOSE 8000

WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
