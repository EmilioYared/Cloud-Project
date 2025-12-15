import os
os.environ['SENTENCE_TRANSFORMERS_HOME'] = './models'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['USE_TORCH'] = '1'
os.environ['USE_TF'] = '0'

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_embedding_model = None
COLLECTION_NAME = "documents"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 produces 384-dimensional vectors


def get_qdrant_client():
    qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
    qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
    logger.info(f"Connecting to Qdrant at {qdrant_host}:{qdrant_port}")
    return QdrantClient(host=qdrant_host, port=qdrant_port)


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model (first time only)...")
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
        
        if not text.strip():
            raise ValueError("No text could be extracted from PDF")
        
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {str(e)}")
        raise


def chunk_text(text, chunk_size=500, overlap=50):
    if not text or not text.strip():
        raise ValueError("Cannot chunk empty text")
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks


def ingest_pdf(pdf_path, doc_name, doc_id=None):
    if doc_id is None:
        doc_id = str(uuid.uuid4())
    
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not doc_name or not doc_name.strip():
        raise ValueError("Document name cannot be empty")
    
    logger.info(f"Starting ingestion for doc_id={doc_id}, name={doc_name}")
    
    try:
        text = extract_text_from_pdf(pdf_path)
        logger.info(f"Extracted {len(text)} characters from PDF")
        
        chunks = chunk_text(text)
        logger.info(f"Created {len(chunks)} chunks")
        
        if len(chunks) == 0:
            raise ValueError("No chunks created from PDF")
        
        model = get_embedding_model()
        
        logger.info("Generating embeddings...")
        embeddings = model.encode(chunks, show_progress_bar=False)
        
        logger.info("Connecting to Qdrant...")
        client = get_qdrant_client()
        
        # Create collection if it doesn't exist
        try:
            client.get_collection(collection_name=COLLECTION_NAME)
            logger.info(f"Collection '{COLLECTION_NAME}' already exists")
        except Exception:
            logger.info(f"Creating collection '{COLLECTION_NAME}'")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            )
        
        # Delete existing points with same doc_id
        try:
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector={"filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]}}
            )
            logger.info(f"Deleted existing chunks for doc_id={doc_id}")
        except Exception as e:
            logger.info(f"No existing chunks to delete: {e}")
        
        # Prepare points for insertion
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload={
                        "doc_id": doc_id,
                        "doc_name": doc_name,
                        "chunk_index": i,
                        "text": chunk
                    }
                )
            )
        
        logger.info("Storing embeddings in Qdrant...")
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        
        logger.info(f"Ingestion complete. Stored {len(chunks)} chunks with doc_id={doc_id}")
        return doc_id
    
    except Exception as e:
        logger.error(f"Ingestion failed for {pdf_path}: {str(e)}")
        raise


if __name__ == "__main__":
    pdf_path = "data/books/monopoly_instructions.pdf"
    doc_name = "Monopoly Rules"
    try:
        doc_id = ingest_pdf(pdf_path, doc_name)
        print(f"Success! Document ID: {doc_id}")
    except Exception as e:
        print(f"Error: {str(e)}")