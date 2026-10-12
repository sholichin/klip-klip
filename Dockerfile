# Production Dockerfile for KLIP KLIP (Flat Structure)
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends     ffmpeg     fonts-dejavu-core     fonts-freefont-ttf     curl     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p storage/downloads storage/transcripts storage/exports storage/cache

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port 8000"]
