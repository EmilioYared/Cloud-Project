#!/bin/bash

# RAG API - Local Testing Script for Linux/Mac

set -e

echo "========================================"
echo "RAG API - Local Test"
echo "========================================"
echo ""

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "ERROR: GEMINI_API_KEY environment variable not set"
    echo "Please run: export GEMINI_API_KEY=your-actual-api-key"
    exit 1
fi

echo "[1/5] Setting environment variables..."
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
echo "QDRANT_HOST=$QDRANT_HOST"
echo "QDRANT_PORT=$QDRANT_PORT"
echo ""

echo "[2/5] Checking/Starting Qdrant container..."
if docker ps | grep -q qdrant; then
    echo "Qdrant container already running!"
else
    echo "Qdrant container not running, starting it..."
    docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_data:/qdrant/storage qdrant/qdrant:latest
    echo "Waiting for Qdrant to be ready..."
    sleep 5
    if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
        echo "Qdrant started successfully!"
    else
        echo "ERROR: Qdrant failed to start"
        echo "Check logs: docker logs qdrant"
        exit 1
    fi
fi
echo ""

echo "[3/5] Installing/Checking dependencies..."
pip install -q -r requirements.txt
echo "Dependencies OK"
echo ""

echo "[4/5] Starting FastAPI server..."
echo "Server will start at http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""
echo "========================================"
echo "Test endpoints:"
echo "  Health: http://localhost:8000/health"
echo "  Swagger: http://localhost:8000/docs"
echo "  Upload: POST http://localhost:8000/upload"
echo "  Ask: POST http://localhost:8000/ask"
echo "========================================"
echo ""

python app.py
