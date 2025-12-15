# RAG API - Local Testing Guide

## Quick Start - Local Testing (ChromaDB in Docker)

### 1. Start ChromaDB Container

Terminal 1:
```bash
# Run ChromaDB in Docker
docker run -d --name chromadb -p 8000:8000 -v chromadb_data:/chroma/chroma chromadb/chroma:0.4.22

# Verify it's running
docker ps
curl http://localhost:8000/api/v1/heartbeat
```

**Alternative: Using docker-compose for ChromaDB only**
```bash
# Create a simple docker-compose-chromadb.yml
docker-compose -f docker-compose-chromadb.yml up -d
```

### 2. Setup and Start API

Terminal 2:
```bash
# Activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set environment variables
set CHROMA_HOST=localhost      # Windows
set CHROMA_PORT=8000
set GEMINI_API_KEY=your-key

# export CHROMA_HOST=localhost  # Linux/Mac
# export CHROMA_PORT=8000
# export GEMINI_API_KEY=your-key

# Start API
python app.py
```

### 3. Test via Swagger UI (Easiest)

Open browser: **http://localhost:8000/docs**

#### Upload PDF:
1. Click **POST /upload** → "Try it out"
2. Click "Choose File" → Select your PDF
3. Enter "doc_name": `My Document`
4. Click "Execute"
5. **Copy the `doc_id`** from response

#### Ask Question:
1. Click **POST /ask** → "Try it out"
2. Paste your `doc_id`
3. Enter question: `What is this document about?`
4. Click "Execute"
5. See the answer!

### 4. Test via Command Line (Windows)

```cmd
REM Health check
curl http://localhost:8000/health

REM Upload PDF
curl -X POST http://localhost:8000/upload ^
  -F "file=@data/books/monopoly_instructions.pdf" ^
  -F "doc_name=Monopoly Rules"

REM Copy doc_id from response, then ask:
curl -X POST http://localhost:8000/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"How do you start the game?\",\"doc_id\":\"YOUR_DOC_ID_HERE\"}"
```

### 5. Test via Command Line (Linux/Mac)

```bash
# Health check
curl http://localhost:8000/health

# Upload PDF
curl -X POST http://localhost:8000/upload \
  -F "file=@data/books/monopoly_instructions.pdf" \
  -F "doc_name=Monopoly Rules"

# Copy doc_id from response, then ask:
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"How do you start the game?","doc_id":"YOUR_DOC_ID_HERE"}'
```

---

## Docker Compose Testing

### 1. Create .env file

```bash
# Create .env file
echo GEMINI_API_KEY=your-actual-api-key-here > .env
```

### 2. Build and Start

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 3. Check Status

```bash
# View logs
docker-compose logs -f

# Check running containers
docker-compose ps

# Check ChromaDB health
curl http://localhost:8000/api/v1/heartbeat

# Check API health
curl http://localhost:8001/health
```

### 4. Test the API

**Note**: API runs on port **8001** in Docker Compose (to avoid conflict with ChromaDB)

```bash
# Upload PDF
curl -X POST http://localhost:8001/upload \
  -F "file=@data/books/monopoly_instructions.pdf" \
  -F "doc_name=Monopoly Rules"

# Ask question (use doc_id from upload)
curl -X POST http://localhost:8001/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"How do you start the game?","doc_id":"YOUR_DOC_ID"}'
```

Or use browser: **http://localhost:8001/docs**

### 5. Stop and Clean

```bash
# Stop services
docker-compose down

# Stop and remove volumes (clears all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

---

## Testing Checklist

### Local Testing (ChromaDB in Docker) ✓
- [ ] ChromaDB container running on port 8000
- [ ] ChromaDB health check passes
- [ ] API server running on localhost:8000
- [ ] API health check returns OK
- [ ] Can upload PDF successfully
- [ ] Receive valid doc_id
- [ ] Can ask questions with doc_id
- [ ] Receive relevant answers

### Docker Compose Testing ✓
- [ ] `docker-compose up` builds successfully
- [ ] Both containers running (chromadb, rag-api)
- [ ] ChromaDB health check passes
- [ ] API health check passes (port 8001)
- [ ] Can upload PDF via Docker API
- [ ] Can ask questions via Docker API
- [ ] Data persists after restart

### Issues to Check
- [ ] ChromaDB connection errors → Check CHROMA_HOST/PORT
- [ ] GEMINI_API_KEY not set → Check environment variables
- [ ] PDF upload fails → Check file size/format
- [ ] Empty answers → Verify doc_id matches upload
- [ ] Out of memory → Close other applications

---

## Example Test Session

```bash
# 1. Start ChromaDB in Docker
docker run -d --name chromadb -p 8000:8000 -v chromadb_data:/chroma/chroma chromadb/chroma:0.4.22

# Verify ChromaDB is running
curl http://localhost:8000/api/v1/heartbeat
# Output: {"nanosecond heartbeat":...}

# 2. In new terminal, start API
set CHROMA_HOST=localhost
set CHROMA_PORT=8000
set GEMINI_API_KEY=your-key
python app.py

# 3. In new terminal, test
curl http://localhost:8000/health
# Output: {"status":"ok","service":"RAG API"}

curl -X POST http://localhost:8000/upload \
  -F "file=@test.pdf" \
  -F "doc_name=Test Doc"
# Output: {"doc_id":"abc-123-xyz","doc_name":"Test Doc","message":"..."}

curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Summarize this document","doc_id":"abc-123-xyz"}'
# Output: {"answer":"This document discusses...","doc_id":"abc-123-xyz","question":"..."}
```

---

## Troubleshootingcontainer is running
docker ps | grep chromadb

# Check ChromaDB health
curl http://localhost:8000/api/v1/heartbeat

# Check container logs
docker logs chromadb

# Restart if needed
docker restart chromadb
### ChromaDB Connection Failed
```bash
# Check if ChromaDB is running
curl http://localhost:8000/api/v1/heartbeat

# Check environment variables
echo %CHROMA_HOST%  # Windows
echo $CHROMA_HOST   # Linux/Mac
```

### API Won't Start
```bash
# Check port availability
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Linux/Mac

# Check dependencies
pip list | grep -E "chromadb|fastapi|sentence"
```

### Upload Fails
```bash
# Check file exists
dir data\books\monopoly_instructions.pdf  # Windows
ls -la data/books/monopoly_instructions.pdf  # Linux/Mac

# Check file size (should be < 50MB)
# Check PDF is valid (open in PDF reader)
```

### Empty/Wrong Answers
```bash
# Verify doc_id matches
# Check ChromaDB has data
curl http://localhost:8000/api/v1/collections

# Check logs for errors
# Check GEMINI_API_KEY is valid
```

---

## Next Steps

After successful local and Docker testing:

1. **K3s Local Testing**: Test Helm chart on local k3s
2. **AWS EC2 Deployment**: Deploy to production
3. **Monitoring Setup**: Add logging and metrics
4. **Performance Testing**: Test with multiple PDFs
5. **Security Hardening**: Add authentication, rate limiting
