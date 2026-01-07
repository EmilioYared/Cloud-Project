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


_embedding_model = None
_gemini_client = None
COLLECTION_NAME = "documents"


def get_qdrant_client():
    qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
    qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
    return QdrantClient(host=qdrant_host, port=qdrant_port)


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def answer_question(question, doc_id, conversation_history=None):
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
    
    if not doc_id or not doc_id.strip():
        raise ValueError("Document ID cannot be empty")
    
    if conversation_history is None:
        conversation_history = []
    
    try:
        client = get_gemini_client()
        model = get_embedding_model()
        
        query_embedding = model.encode([question], show_progress_bar=False)[0]
        
        qdrant_client = get_qdrant_client()
        
        try:
            qdrant_client.get_collection(collection_name=COLLECTION_NAME)
        except Exception as e:
            raise ValueError(f"Qdrant collection '{COLLECTION_NAME}' not found. Please ingest documents first. Error: {str(e)}")
        
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding.tolist(),
            query_filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
            limit=3
        )
        
        if not search_result:
            return f"No context found for document ID: {doc_id}. Please verify the document was uploaded successfully."
        
        retrieved_chunks = [hit.payload["text"] for hit in search_result]
        
        
        if len(retrieved_chunks) == 0:
            return f"No relevant context found for document ID: {doc_id}"
        
        context = "\n\n".join(retrieved_chunks)
        
        # Build conversation history string if available
        history_text = ""
        if conversation_history:
            history_lines = []
            for msg in conversation_history:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                history_lines.append(f"{role_label}: {msg['content']}")
            history_text = f"""\n\nPrevious Conversation:\n{chr(10).join(history_lines)}\n"""
        
        prompt = f"""You are answering questions using ONLY the context below.
If the answer is not contained in the context, say "I don't know".
{history_text}
Context:
{context}

Question:
{question}

Answer:"""
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        answer = response.text
        
        return answer
    
    except ValueError as ve:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to generate answer: {str(e)}")