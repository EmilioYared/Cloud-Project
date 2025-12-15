@echo off
REM RAG API - Local Testing Script for Windows

echo ========================================
echo RAG API - Local Test
echo ========================================
echo.

REM Check if GEMINI_API_KEY is set
if "%GEMINI_API_KEY%"=="" (
    echo ERROR: GEMINI_API_KEY environment variable not set
    echo Please run: set GEMINI_API_KEY=your-actual-api-key
    exit /b 1
)

echo [1/5] Setting environment variables...
set QDRANT_HOST=localhost
set QDRANT_PORT=6333
echo QDRANT_HOST=%QDRANT_HOST%
echo QDRANT_PORT=%QDRANT_PORT%
echo.

echo [2/5] Checking/Starting Qdrant container...
docker ps | findstr qdrant >nul 2>&1
if errorlevel 1 (
    echo Qdrant container not running, starting it...
    docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_data:/qdrant/storage qdrant/qdrant:latest
    echo Waiting for Qdrant to be ready...
    timeout /t 5 /nobreak >nul
    curl -s http://localhost:6333/healthz >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Qdrant failed to start
        echo Check logs: docker logs qdrant
        exit /b 1
    )
    echo Qdrant started successfully!
) else (
    echo Qdrant container already running!
)
echo.

echo [3/5] Installing/Checking dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)
echo Dependencies OK
echo.

echo [4/5] Starting FastAPI server...
echo Server will start at http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo Test endpoints:
echo   Health: http://localhost:8000/health
echo   Swagger: http://localhost:8000/docs
echo   Upload: POST http://localhost:8000/upload
echo   Ask: POST http://localhost:8000/ask
echo ========================================
echo.

python app.py
