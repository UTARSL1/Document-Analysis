FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    ghostscript \
    poppler-utils \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY processing /app/processing
COPY templates /app/templates
COPY config /app/config

ENV PYTHONPATH=/app
ENV UPLOAD_DIR=/data/uploads
ENV ARTIFACT_DIR=/data/artifacts

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
