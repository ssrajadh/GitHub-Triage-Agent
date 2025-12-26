"""
RAG (Retrieval-Augmented Generation) Service
Vector database operations for context retrieval
"""
import logging
import os
from pathlib import Path
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


async def search_relevant_context(query: str, top_k: int = 10) -> List[str]:
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
        # Resolve path relative to backend directory (where this file is located)
        backend_dir = Path(__file__).parent.parent
        default_path = backend_dir / "chroma_db"
        
        env_path = os.getenv("CHROMA_PERSIST_DIRECTORY")
        if env_path:
            # If env var is set, resolve it (could be absolute or relative)
            persist_directory = Path(env_path)
            if not persist_directory.is_absolute():
                # If relative, resolve from backend directory
                persist_directory = backend_dir / persist_directory
            persist_directory = str(persist_directory.resolve())
        else:
            # Use default path (already absolute from backend_dir)
            persist_directory = str(default_path.resolve())
        
        # Check if database exists
        if not os.path.exists(persist_directory):
            logger.warning(f"Vector database not found at {persist_directory}")
            return []
        
        # Initialize embeddings and vector store
        embeddings = OpenAIEmbeddings()
        collection_name = os.getenv("CHROMA_COLLECTION_NAME", "repository_docs")
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings,
            collection_name=collection_name
        )
        
        # Perform similarity search with metadata filtering to get diverse results
        results = vectorstore.similarity_search(query, k=top_k)
        
        # Extract text from results with source information
        context_chunks = []
        seen_sources = set()
        
        for doc in results:
            # Include source file path if available in metadata
            source = doc.metadata.get('source', 'unknown')
            chunk_text = doc.page_content
            
            # Prepend source info to help LLM understand context
            if source != 'unknown':
                context_chunks.append(f"[From: {source}]\n{chunk_text}")
                seen_sources.add(source)
            else:
                context_chunks.append(chunk_text)
        
        logger.info(f"Retrieved {len(context_chunks)} chunks from {len(seen_sources)} unique files")
        if context_chunks and results:
            sample_sources = [doc.metadata.get('source', 'unknown') for doc in results[:5]]
            logger.info(f"Top sources: {sample_sources}")
        return context_chunks
        
    except Exception as e:
        logger.error(f"Error searching vector database: {str(e)}")
        return []


def get_vectorstore_stats() -> dict:
    """Get statistics about the vector database"""
    if not HAS_CHROMA:
        return {"error": "ChromaDB not available"}
    
    try:
        # Resolve path relative to backend directory (where this file is located)
        backend_dir = Path(__file__).parent.parent
        default_path = backend_dir / "chroma_db"
        collection_name = os.getenv("CHROMA_COLLECTION_NAME", "repository_docs")
        
        env_path = os.getenv("CHROMA_PERSIST_DIRECTORY")
        if env_path:
            # If env var is set, resolve it (could be absolute or relative)
            persist_directory = Path(env_path)
            if not persist_directory.is_absolute():
                # If relative, resolve from backend directory
                persist_directory = backend_dir / persist_directory
            persist_directory = str(persist_directory.resolve())
        else:
            # Use default path (already absolute from backend_dir)
            persist_directory = str(default_path.resolve())
        
        if not os.path.exists(persist_directory):
            return {"error": "Database not initialized"}
        
        client = chromadb.PersistentClient(path=persist_directory)
        collections = client.list_collections()
        
        stats = {
            "collections": len(collections),
            "details": [],
            "active_collection": collection_name
        }
        
        for collection in collections:
            stats["details"].append({
                "name": collection.name,
                "count": collection.count()
            })
        
        # Check if the active collection exists
        collection_names = [c.name for c in collections]
        if collection_name not in collection_names:
            stats["warning"] = f"Collection '{collection_name}' not found. Available: {collection_names}"
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting vectorstore stats: {str(e)}")
        return {"error": str(e)}
