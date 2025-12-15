import os
os.environ['SENTENCE_TRANSFORMERS_HOME'] = './models'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['USE_TORCH'] = '1'
os.environ['USE_TF'] = '0'

from dotenv import load_dotenv
load_dotenv()

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from google import genai
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_embedding_model = None
_gemini_client = None
COLLECTION_NAME = "documents"


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


def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        logger.info("Initializing Gemini client (first time only)...")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def answer_question(question, doc_id):
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
    
    if not doc_id or not doc_id.strip():
        raise ValueError("Document ID cannot be empty")
    
    logger.info(f"Processing question for doc_id={doc_id}")
    logger.info(f"Question: {question[:100]}...")
    
    try:
        client = get_gemini_client()
        model = get_embedding_model()
        
        logger.info("Generating query embedding...")
        query_embedding = model.encode([question], show_progress_bar=False)[0]
        
        logger.info("Connecting to Qdrant...")
        qdrant_client = get_qdrant_client()
        
        try:
            qdrant_client.get_collection(collection_name=COLLECTION_NAME)
        except Exception as e:
            raise ValueError(f"Qdrant collection '{COLLECTION_NAME}' not found. Please ingest documents first. Error: {str(e)}")
        
        logger.info(f"Querying Qdrant for doc_id={doc_id}...")
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding.tolist(),
            query_filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
            limit=3
        )
        
        if not search_result:
            logger.warning(f"No chunks found for doc_id={doc_id}")
            return f"No context found for document ID: {doc_id}. Please verify the document was uploaded successfully."
        
        retrieved_chunks = [hit.payload["text"] for hit in search_result]
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks")
        
        if len(retrieved_chunks) == 0:
            return f"No relevant context found for document ID: {doc_id}"
        
        context = "\n\n".join(retrieved_chunks)
        
        prompt = f"""You are answering questions using ONLY the context below.
If the answer is not contained in the context, say "I don't know".

Context:
{context}

Question:
{question}"""
        
        logger.info("Calling Gemini API...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        answer = response.text
        logger.info(f"Answer generated: {answer[:100]}...")
        
        return answer
    
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise RuntimeError(f"Failed to generate answer: {str(e)}")