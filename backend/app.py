import os
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import uuid
import shutil
from pathlib import Path
import logging
from ingest import ingest_pdf, get_qdrant_client, COLLECTION_NAME
from rag import answer_question
from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG API",
    description="Document-based Question Answering with RAG",
    version="1.0.0"
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # For development - allows all origins
        # In production, replace with your S3 bucket URL:
        # "http://your-bucket-name.s3-website-us-east-1.amazonaws.com",
        # "https://your-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


class ConversationMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: str = Field(..., description="Content of the message")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to ask about the document")
    doc_id: str = Field(..., min_length=1, description="Document ID from upload")
    conversation_history: List[ConversationMessage] = Field(default=[], description="Previous conversation messages for context")


class UploadResponse(BaseModel):
    doc_id: str
    doc_name: str
    message: str
    chunks_stored: int = None


class AskResponse(BaseModel):
    answer: str
    doc_id: str
    question: str


class DocumentInfo(BaseModel):
    doc_id: str
    doc_name: str
    chunk_count: int = Field(default=0, description="Number of chunks stored for this document")


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
    total: int


class DeleteResponse(BaseModel):
    doc_id: str
    doc_name: str = None
    deleted_chunks: int
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: str = None


@app.get("/documents", response_model=DocumentListResponse, responses={500: {"model": ErrorResponse}})
async def list_documents():
    """
    Get list of all documents stored in Qdrant.
    
    Returns document IDs, names, and chunk counts for all ingested PDFs.
    """
    try:
        client = get_qdrant_client()
        
        # Get collection info to check if it exists
        try:
            collection_info = client.get_collection(COLLECTION_NAME)
        except Exception:
            # Collection doesn't exist yet
            return DocumentListResponse(documents=[], total=0)
        
        # Scroll through all points to get unique documents
        documents_dict = {}
        offset = None
        
        while True:
            # Fetch points in batches
            result = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            points, offset = result
            
            if not points:
                break
            
            # Extract unique documents from point payloads
            for point in points:
                if point.payload:
                    doc_id = point.payload.get('doc_id')
                    doc_name = point.payload.get('doc_name')
                    
                    if doc_id:
                        if doc_id not in documents_dict:
                            documents_dict[doc_id] = {
                                'doc_id': doc_id,
                                'doc_name': doc_name or 'Unknown',
                                'chunk_count': 0
                            }
                        documents_dict[doc_id]['chunk_count'] += 1
            
            # If no offset returned, we've reached the end
            if offset is None:
                break
        
        documents = [
            DocumentInfo(**doc_info)
            for doc_info in documents_dict.values()
        ]
        
        # Sort by doc_name for consistent ordering
        documents.sort(key=lambda x: x.doc_name)
        
        logger.info(f"Found {len(documents)} documents in Qdrant")
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents)
        )
    
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")


@app.delete("/documents/{doc_id}", response_model=DeleteResponse, responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def delete_document(doc_id: str):
    """
    Delete a document and all its embeddings from Qdrant.
    
    - **doc_id**: The UUID of the document to delete
    
    Returns information about the deleted document.
    """
    try:
        client = get_qdrant_client()
        
        # First, check if collection exists
        try:
            collection_info = client.get_collection(COLLECTION_NAME)
        except Exception:
            raise HTTPException(status_code=404, detail="No documents found in the system")
        
        # Get document info before deletion
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
            limit=1,
            with_payload=True,
            with_vectors=False
        )
        
        points, _ = result
        
        if not points:
            raise HTTPException(status_code=404, detail=f"Document with ID {doc_id} not found")
        
        doc_name = points[0].payload.get('doc_name', 'Unknown')
        
        # Count chunks before deletion
        count_result = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
            limit=10000,
            with_payload=False,
            with_vectors=False
        )
        
        all_points, _ = count_result
        chunk_count = len(all_points)
        
        # Delete all points with this doc_id
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                )
            )
        )
        
        logger.info(f"Deleted document {doc_id} ({doc_name}) with {chunk_count} chunks")
        
        return DeleteResponse(
            doc_id=doc_id,
            doc_name=doc_name,
            deleted_chunks=chunk_count,
            message=f"Document '{doc_name}' and all {chunk_count} chunks deleted successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")


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
    
    logger.info(f"Received upload request: file={file.filename}, doc_name={doc_name}, doc_id={doc_id}")
    
    try:
        # Use temporary file that gets auto-deleted after processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = Path(temp_file.name)
            
            shutil.copyfileobj(file.file, temp_file)
            temp_file.flush()
            
            logger.info(f"File saved to temporary location: {temp_path}")
            
            file_size = temp_path.stat().st_size
            if file_size == 0:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            
            logger.info(f"File size: {file_size} bytes")
            
            doc_id, chunks_stored = ingest_pdf(str(temp_path), doc_name, doc_id)
            
            return UploadResponse(
                doc_id=doc_id,
                doc_name=doc_name,
                message="PDF uploaded and ingested successfully",
                chunks_stored=chunks_stored
            )
    
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error(f"Validation error during ingestion: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        # Always delete temp file after processing
        if 'temp_path' in locals() and temp_path.exists():
            temp_path.unlink()
            logger.info(f"Temporary file deleted: {temp_path}")
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
        # Convert conversation history to list of dicts
        history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
        answer = answer_question(request.question, request.doc_id, history)
        
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
