FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- FIX: Clear compiled Python files and corrupted bytecode ---
RUN find /usr/local/lib/python* -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
RUN find /usr/local/lib/python* -name '*.pyc' -exec rm -f {} + 2>/dev/null || true

# Copy application code
COPY *.py ./

# Create necessary directories
RUN mkdir -p /app/models

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    SENTENCE_TRANSFORMERS_HOME=/app/models \
    TRANSFORMERS_VERBOSITY=error \
    USE_TORCH=1 \
    USE_TF=0

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
