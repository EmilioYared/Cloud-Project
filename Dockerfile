FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

COPY app.py ingest.py rag.py ./

RUN mkdir -p /app/uploads /app/models

ENV PYTHONUNBUFFERED=1
ENV SENTENCE_TRANSFORMERS_HOME=/app/models
ENV TRANSFORMERS_VERBOSITY=error
ENV USE_TORCH=1
ENV USE_TF=0

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
