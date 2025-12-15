import os
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uuid
import shutil
from pathlib import Path
import logging
from ingest import ingest_pdf
from rag import answer_question

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG API",
    description="Document-based Question Answering with RAG",
    version="1.0.0"
)

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to ask about the document")
    doc_id: str = Field(..., min_length=1, description="Document ID from upload")


class UploadResponse(BaseModel):
    doc_id: str
    doc_name: str
    message: str
    chunks_stored: int = None


class AskResponse(BaseModel):
    answer: str
    doc_id: str
    question: str


class ErrorResponse(BaseModel):
    error: str
    detail: str = None


@app.post("/upload", response_model=UploadResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def upload_pdf(file: UploadFile = File(...), doc_name: str = Form(None)):
    """
    Upload a PDF document and ingest it into the RAG system.
    
    - **file**: PDF file to upload
    - **doc_name**: Optional name for the document (defaults to filename)
    
    Returns the document ID to use for querying.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    doc_id = str(uuid.uuid4())
    
    if doc_name is None or not doc_name.strip():
        doc_name = Path(file.filename).stem
    
    doc_name = doc_name.strip()
    file_path = UPLOAD_DIR / f"{doc_id}.pdf"
    
    logger.info(f"Received upload request: file={file.filename}, doc_name={doc_name}, doc_id={doc_id}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved to {file_path}")
        
        file_size = file_path.stat().st_size
        if file_size == 0:
            file_path.unlink()
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        logger.info(f"File size: {file_size} bytes")
        
        ingest_pdf(str(file_path), doc_name, doc_id)
        
        return UploadResponse(
            doc_id=doc_id,
            doc_name=doc_name,
            message="PDF uploaded and ingested successfully"
        )
    
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error(f"Validation error during ingestion: {str(ve)}")
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}", exc_info=True)
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        file.file.close()


@app.post("/ask", response_model=AskResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def ask_question_endpoint(request: AskRequest):
    """
    Ask a question about a previously uploaded document.
    
    - **question**: The question to ask
    - **doc_id**: The document ID from the upload response
    
    Returns an answer based on the document content.
    """
    logger.info(f"Received question for doc_id={request.doc_id}: {request.question[:100]}...")
    
    try:
        answer = answer_question(request.question, request.doc_id)
        
        return AskResponse(
            answer=answer,
            doc_id=request.doc_id,
            question=request.question
        )
    
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        logger.error(f"Runtime error: {str(re)}")
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        logger.error(f"Unexpected error answering question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "RAG API"}


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "RAG API",
        "version": "1.0.0",
        "endpoints": {
            "POST /upload": "Upload a PDF document",
            "POST /ask": "Ask a question about a document",
            "GET /health": "Health check",
            "GET /docs": "API documentation"
        }
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting RAG API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
