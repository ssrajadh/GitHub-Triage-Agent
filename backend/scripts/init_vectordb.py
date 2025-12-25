#!/usr/bin/env python3
"""
Vector Database Initialization Script for GitHub Triage Agent

This script indexes a target repository's documentation and code into ChromaDB,
enabling the RAG (Retrieval-Augmented Generation) system to provide context-aware
responses to GitHub issues.

Usage:
    python scripts/init_vectordb.py --repo-path /path/to/target/repo
    python scripts/init_vectordb.py --repo-path /path/to/target/repo --chunk-size 1500 --overlap 300
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class RepositoryIndexer:
    """
    Indexes repository files into a vector database for semantic search.
    
    The indexer processes documentation files (markdown, text) and source code
    (Python, C++, JavaScript, etc.) to create searchable embeddings that enable
    the AI agent to find relevant context when analyzing GitHub issues.
    """
    
    # File extensions to index
    SUPPORTED_EXTENSIONS = {
        # Documentation
        '.md', '.txt', '.rst', '.adoc',
        # Code files
        '.py', '.js', '.ts', '.jsx', '.tsx',
        '.cpp', '.hpp', '.c', '.h', '.cc',
        '.java', '.go', '.rs', '.rb',
        '.php', '.cs', '.swift', '.kt',
        # Config files
        '.json', '.yaml', '.yml', '.toml', '.ini',
        # Other
        '.proto', '.sql', '.sh', '.bash'
    }
    
    # Directories to skip
    SKIP_DIRS = {
        '.git', '__pycache__', 'node_modules', 'venv', 'env',
        '.venv', 'dist', 'build', '.pytest_cache', '.mypy_cache',
        'coverage', '.tox', 'htmlcov', 'wheels', '.eggs',
        'site-packages', 'vendor', 'target'
    }
    
    def __init__(
        self,
        repo_path: str,
        persist_directory: str = "./chroma_db",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        collection_name: str = "repository_docs"
    ):
        """
        Initialize the repository indexer.
        
        Args:
            repo_path: Path to the repository to index
            persist_directory: Directory where ChromaDB will store data
            chunk_size: Size of text chunks for splitting documents
            chunk_overlap: Overlap between consecutive chunks
            collection_name: Name of the ChromaDB collection
        """
        self.repo_path = Path(repo_path).resolve()
        self.persist_directory = persist_directory
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.collection_name = collection_name
        
        # Validate repository path
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")
        
        # Initialize text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize OpenAI embeddings
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",  # Cost-effective embedding model
            openai_api_key=api_key
        )
        
        logger.info(f"Initialized RepositoryIndexer for: {self.repo_path}")
    
    def collect_files(self) -> List[Path]:
        """
        Recursively collect all relevant files from the repository.
        
        Returns:
            List of file paths to index
        """
        files = []
        
        for file_path in self.repo_path.rglob("*"):
            # Skip if it's a directory
            if file_path.is_dir():
                continue
            
            # Skip if in excluded directory
            if any(skip_dir in file_path.parts for skip_dir in self.SKIP_DIRS):
                continue
            
            # Check if file extension is supported
            if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                files.append(file_path)
        
        logger.info(f"Found {len(files)} files to index")
        return files
    
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from a file for better retrieval.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing file metadata
        """
        relative_path = file_path.relative_to(self.repo_path)
        
        return {
            "source": str(relative_path),
            "file_type": file_path.suffix[1:],  # Remove leading dot
            "file_name": file_path.name,
            "directory": str(relative_path.parent),
            "absolute_path": str(file_path)
        }
    
    def read_file_content(self, file_path: Path) -> str:
        """
        Read file content with encoding fallback.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content as string
        """
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
                return ""
        
        logger.warning(f"Could not decode {file_path} with any encoding")
        return ""
    
    def create_documents(self, files: List[Path]) -> List[Document]:
        """
        Create LangChain Document objects from files.
        
        Args:
            files: List of file paths
            
        Returns:
            List of Document objects with content and metadata
        """
        documents = []
        
        for i, file_path in enumerate(files, 1):
            logger.info(f"Processing {i}/{len(files)}: {file_path.name}")
            
            # Read file content
            content = self.read_file_content(file_path)
            
            if not content.strip():
                logger.warning(f"Skipping empty file: {file_path}")
                continue
            
            # Extract metadata
            metadata = self.extract_metadata(file_path)
            
            # Create document
            doc = Document(page_content=content, metadata=metadata)
            
            # Split into chunks
            chunks = self.text_splitter.split_documents([doc])
            
            # Add chunk index to metadata
            for idx, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = idx
                chunk.metadata["total_chunks"] = len(chunks)
            
            documents.extend(chunks)
            
            logger.debug(f"Created {len(chunks)} chunks from {file_path.name}")
        
        logger.info(f"Created {len(documents)} document chunks from {len(files)} files")
        return documents
    
    def index_documents(self, documents: List[Document]) -> Chroma:
        """
        Index documents into ChromaDB vector store.
        
        Args:
            documents: List of Document objects to index
            
        Returns:
            Chroma vector store instance
        """
        logger.info(f"Indexing {len(documents)} documents into ChromaDB...")
        
        # Create or load vector store
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
            collection_name=self.collection_name,
            collection_metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        logger.info(f"Successfully indexed documents into: {self.persist_directory}")
        return vectorstore
    
    def run(self) -> Chroma:
        """
        Execute the full indexing pipeline.
        
        Returns:
            Chroma vector store instance
        """
        logger.info("Starting repository indexing...")
        
        # Step 1: Collect files
        files = self.collect_files()
        
        if not files:
            logger.warning("No files found to index!")
            return None
        
        # Step 2: Create documents with chunks
        documents = self.create_documents(files)
        
        if not documents:
            logger.warning("No documents created!")
            return None
        
        # Step 3: Index into vector database
        vectorstore = self.index_documents(documents)
        
        logger.info("✓ Indexing complete!")
        
        # Verify indexing
        self.verify_index(vectorstore)
        
        return vectorstore
    
    def verify_index(self, vectorstore: Chroma):
        """
        Verify that the index was created successfully.
        
        Args:
            vectorstore: Chroma vector store to verify
        """
        logger.info("Verifying index...")
        
        try:
            # Test query
            test_query = "error handling and exception management"
            results = vectorstore.similarity_search(test_query, k=3)
            
            logger.info(f"Test query returned {len(results)} results")
            
            if results:
                logger.info(f"Sample result: {results[0].metadata.get('source', 'unknown')}")
            
            # Get collection stats
            collection = vectorstore._collection
            count = collection.count()
            logger.info(f"Total documents in collection: {count}")
            
        except Exception as e:
            logger.error(f"Error verifying index: {e}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Initialize vector database for GitHub Triage Agent RAG system"
    )
    
    parser.add_argument(
        "--repo-path",
        type=str,
        required=True,
        help="Path to the repository to index"
    )
    
    parser.add_argument(
        "--persist-dir",
        type=str,
        default="./chroma_db",
        help="Directory to persist ChromaDB data (default: ./chroma_db)"
    )
    
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Size of text chunks (default: 1000)"
    )
    
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Overlap between chunks (default: 200)"
    )
    
    parser.add_argument(
        "--collection-name",
        type=str,
        default="repository_docs",
        help="Name of the ChromaDB collection (default: repository_docs)"
    )
    
    args = parser.parse_args()
    
    try:
        # Create indexer
        indexer = RepositoryIndexer(
            repo_path=args.repo_path,
            persist_directory=args.persist_dir,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            collection_name=args.collection_name
        )
        
        # Run indexing
        vectorstore = indexer.run()
        
        if vectorstore:
            print("\n" + "="*60)
            print("✓ Vector database initialized successfully!")
            print(f"✓ Location: {args.persist_dir}")
            print(f"✓ Collection: {args.collection_name}")
            print("="*60)
            return 0
        else:
            print("\n✗ Failed to initialize vector database")
            return 1
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
