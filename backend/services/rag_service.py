"""
RAG (Retrieval-Augmented Generation) Service
Vector database operations for context retrieval
"""
import logging
import os
from typing import List

logger = logging.getLogger(__name__)

# Check if ChromaDB is available
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMA = True
except ImportError:
    logger.warning("ChromaDB not available - RAG features disabled")
    HAS_CHROMA = False

# Check if OpenAI is available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HAS_OPENAI = bool(OPENAI_API_KEY)

if HAS_OPENAI and HAS_CHROMA:
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_community.vectorstores import Chroma
    except ImportError:
        logger.warning("LangChain components not available")
        HAS_OPENAI = False


async def search_relevant_context(query: str, top_k: int = 5) -> List[str]:
    """
    Search vector database for relevant context
    
    Args:
        query: User's issue text
        top_k: Number of results to return
        
    Returns:
        List of relevant text chunks
    """
    if not HAS_CHROMA or not HAS_OPENAI:
        logger.warning("RAG not configured - returning mock context")
        return [
            "Mock context: This is sample documentation for testing purposes.",
            "Mock context: Configure ChromaDB and OpenAI API for real retrieval."
        ]
    
    try:
        persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        
        # Check if database exists
        if not os.path.exists(persist_directory):
            logger.warning(f"Vector database not found at {persist_directory}")
            return []
        
        # Initialize embeddings and vector store
        embeddings = OpenAIEmbeddings()
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
        
        # Perform similarity search
        results = vectorstore.similarity_search(query, k=top_k)
        
        # Extract text from results
        context_chunks = [doc.page_content for doc in results]
        
        logger.info(f"Retrieved {len(context_chunks)} chunks from vector database")
        return context_chunks
        
    except Exception as e:
        logger.error(f"Error searching vector database: {str(e)}")
        return []


def get_vectorstore_stats() -> dict:
    """Get statistics about the vector database"""
    if not HAS_CHROMA:
        return {"error": "ChromaDB not available"}
    
    try:
        persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        
        if not os.path.exists(persist_directory):
            return {"error": "Database not initialized"}
        
        client = chromadb.PersistentClient(path=persist_directory)
        collections = client.list_collections()
        
        stats = {
            "collections": len(collections),
            "details": []
        }
        
        for collection in collections:
            stats["details"].append({
                "name": collection.name,
                "count": collection.count()
            })
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting vectorstore stats: {str(e)}")
        return {"error": str(e)}
