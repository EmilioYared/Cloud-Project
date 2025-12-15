# Local Testing with Qdrant in Docker

Complete guide for testing your RAG API locally with Qdrant running in Docker.

## Why Qdrant?

✅ **Stable in Docker**: No weird crashes or downloads  
✅ **Production-Ready**: Battle-tested vector database  
✅ **Fast**: Optimized for similarity search  
✅ **Easy to Use**: Clean API and great documentation  

---

## Quick Start (Recommended)

### Option 1: Automated Script (Easiest)

```cmd
REM Windows
set GEMINI_API_KEY=your-actual-key
test-local.bat
```

```bash
# Linux/Mac
export GEMINI_API_KEY=your-actual-key
bash test-local.sh
```

The script automatically:
- Starts Qdrant container if not running
- Sets environment variables
- Installs dependencies
- Starts the API server

### Option 2: Manual Steps

**Step 1: Start Qdrant Container**

```bash
# Run Qdrant in Docker
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_data:/qdrant/storage \
  qdrant/qdrant:latest

# Verify it's running
docker ps
curl http://localhost:6333/healthz
```

**Step 2: Setup Python Environment**

```bash
# Create virtual environment (if not exists)
python -m venv venv

# Activate it
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

**Step 3: Set Environment Variables**

```cmd
REM Windows
set QDRANT_HOST=localhost
set QDRANT_PORT=6333
set GEMINI_API_KEY=your-key
```

```bash
# Linux/Mac
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export GEMINI_API_KEY=your-actual-key
```

**Step 4: Start API**

```bash
python app.py
```

API runs at: **http://localhost:8000**

---

## Testing via Browser (Easiest)

Open: **http://localhost:8000/docs**

### Upload a PDF:

1. Expand **POST /upload**
2. Click "Try it out"
3. Click "Choose File" → Select your PDF
4. Enter `doc_name`: e.g., "My Document"
5. Click "Execute"
6. **Copy the `doc_id`** from the response

### Ask a Question:

1. Expand **POST /ask**
2. Click "Try it out"
3. Paste your `doc_id`
4. Enter `question`: e.g., "What is this document about?"
5. Click "Execute"
6. See the AI-generated answer!

---

## Testing via Command Line

### Windows (CMD)

```cmd
REM Health check
curl http://localhost:8000/health

REM Upload PDF
curl -X POST http://localhost:8000/upload ^
  -F "file=@data/books/monopoly_instructions.pdf" ^
  -F "doc_name=Monopoly Rules"

REM Note the doc_id from response, then:
curl -X POST http://localhost:8000/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"How do you start the game?\",\"doc_id\":\"YOUR_DOC_ID_HERE\"}"
```

### Linux/Mac

```bash
# Health check
curl http://localhost:8000/health

# Upload PDF
curl -X POST http://localhost:8000/upload \
  -F "file=@data/books/monopoly_instructions.pdf" \
  -F "doc_name=Monopoly Rules"

# Note the doc_id from response, then:
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"How do you start the game?","doc_id":"YOUR_DOC_ID_HERE"}'
```

---

## Managing Qdrant Container

### Start/Stop

```bash
# Start
docker start qdrant

# Stop
docker stop qdrant

# Restart
docker restart qdrant

# Check status
docker ps | grep qdrant
```

### View Logs

```bash
# All logs
docker logs qdrant

# Follow logs
docker logs -f qdrant

# Last 50 lines
docker logs --tail 50 qdrant
```

### Check Health

```bash
# Qdrant health
curl http://localhost:6333/healthz

# List collections
curl http://localhost:6333/collections

# Get collection info
curl http://localhost:6333/collections/documents

# Qdrant metrics
curl http://localhost:6333/metrics
```

### Clean Up

```bash
# Stop and remove container
docker stop qdrant
docker rm qdrant

# Remove data (WARNING: deletes all documents!)
docker volume rm qdrant_data

# Or remove everything
docker stop qdrant && docker rm qdrant && docker volume rm qdrant_data
```

---

## Alternative: Use docker-compose for Qdrant

```bash
# Start Qdrant using docker-compose
docker-compose -f docker-compose-chromadb.yml up -d

# Check status
docker-compose -f docker-compose-chromadb.yml ps

# View logs
docker-compose -f docker-compose-chromadb.yml logs -f

# Stop
docker-compose -f docker-compose-chromadb.yml down

# Stop and remove data
docker-compose -f docker-compose-chromadb.yml down -v
```

---

## Complete Test Example

```bash
# 1. Start Qdrant (one-time)
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_data:/qdrant/storage qdrant/qdrant:latest

# 2. Verify Qdrant
curl http://localhost:6333/healthz
# Expected: {"title":"healthz","version":"..."}

# 3. Setup environment
export GEMINI_API_KEY=your-key
export QDRANT_HOST=localhost
export QDRANT_PORT=6333

# 4. Start API
python app.py
# Server starting at http://0.0.0.0:8000

# 5. In another terminal, test
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"RAG API"}

# 6. Upload PDF
curl -X POST http://localhost:8000/upload \
  -F "file=@test.pdf" \
  -F "doc_name=Test Document"
# Expected: {"doc_id":"abc-123-xyz","doc_name":"Test Document",...}

# 7. Ask question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Summarize this","doc_id":"abc-123-xyz"}'
# Expected: {"answer":"...","doc_id":"abc-123-xyz",...}
```

---
Qdrant container won't start

```bash
# Check if ports are already in use
netstat -ano | findstr :6333  # Windows
lsof -i :6333                  # Linux/Mac

# Check Docker is running
docker version

# Remove old container and restart
docker rm -f qdrant
docker run -d --name qdrant -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant:latest
```

### Connection Refused

```bash
# Make sure container is running
docker ps | grep qdrant

# Check container logs
docker logs qdrant

# Check environment variables
echo %QDRANT_HOST%  # Windows
echo $QDRANT_HOST   # Linux/Mac

# Try connecting from inside container
docker exec qdrant curl http://localhost:6333/healthz
```

### API can't connect to Qdrant

```bash
# Windows: Use 'host.docker.internal' if API also in Docker
set QDRANT_HOST=host.docker.internal

# Or use container name if in same network
set QDRANT_HOST=qdrant

# For local testing (API not in Docker), use:
set QDRANT_HOST=localhost
```

### Data not persisting

```bash
# Check volume exists
docker volume ls | grep qdrant

# Inspect volume
docker volume inspect qdrant_data

# If missing, create it explicitly
docker volume create qdrant_data
docker run -d --name qdrant -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant:latest
```

### Collection not found error

```bash
# List collections
curl http://localhost:6333/collections

# If empty, upload a document first to create the collection
# The collection is created automatically on first document upload
# If missing, create it explicitly
docker Qdrant in Docker works** → Ready for next step
2. **Full Docker Compose** → Test API container + Qdrant together
3. **K3s Local** → Test Helm chart locally
4. **AWS EC2** → Deploy to production

See [TESTING.md](TESTING.md) for full Docker Compose testing guide.

---

## Why Qdrant is Better for Docker

- **No weird downloads**: Qdrant doesn't download models or dependencies at runtime
- **Stable**: No random crashes or memory issues
- **Fast startup**: Ready in seconds
- **Production ready**: Used by many companies in production
- **Great monitoring**: Built-in metrics and health endpoints
- **Easy debugging**: Clear logs and error messages
## Next Steps

After successful local testing:

1. ✅ **ChromaDB in Docker works** → Ready for next step
2. **Full Docker Compose** → Test API container + ChromaDB together
3. **K3s Local** → Test Helm chart locally
4. **AWS EC2** → Deploy to production

See [TESTING.md](TESTING.md) for full Docker Compose testing guide.
