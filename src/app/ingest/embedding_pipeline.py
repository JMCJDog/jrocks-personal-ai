"""Embedding Pipeline - Generate and store embeddings for the knowledge base.

Handles embedding generation using sentence-transformers and storage
in ChromaDB for semantic search capabilities.
"""

from typing import Optional
from dataclasses import dataclass
from pathlib import Path

from .document_processor import DocumentChunk, ProcessedDocument


@dataclass
class EmbeddingConfig:
    """Configuration for the embedding pipeline."""
    
    model_name: str = "all-MiniLM-L6-v2"
    collection_name: str = "jrock_knowledge"
    persist_directory: str = "./data/chromadb"
    batch_size: int = 32


class EmbeddingPipeline:
    """Pipeline for generating embeddings and storing in vector database.
    
    Uses sentence-transformers for embedding generation and ChromaDB
    for vector storage and retrieval.
    
    Example:
        >>> pipeline = EmbeddingPipeline()
        >>> pipeline.add_document(processed_doc)
        >>> results = pipeline.search("AI development")
    """
    
    def __init__(self, config: Optional[EmbeddingConfig] = None) -> None:
        """Initialize the embedding pipeline.
        
        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or EmbeddingConfig()
        self._embedding_model = None
        self._chroma_client = None
        self._collection = None
    
    @property
    def embedding_model(self):
        """Lazy-load the embedding model."""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(self.config.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required. "
                    "Install with: pip install sentence-transformers"
                )
        return self._embedding_model
    
    @property
    def collection(self):
        """Lazy-load the ChromaDB collection."""
        if self._collection is None:
            try:
                import chromadb
                
                # Ensure persist directory exists
                persist_path = Path(self.config.persist_directory)
                persist_path.mkdir(parents=True, exist_ok=True)
                
                # Use modern PersistentClient API (ChromaDB 0.4+)
                self._chroma_client = chromadb.PersistentClient(
                    path=str(persist_path)
                )
                
                self._collection = self._chroma_client.get_or_create_collection(
                    name=self.config.collection_name,
                    metadata={"description": "JRock's Personal AI Knowledge Base"}
                )
            except ImportError:
                raise ImportError(
                    "chromadb is required. Install with: pip install chromadb"
                )
        return self._collection
    
    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed.
        
        Returns:
            list: List of embedding vectors.
        """
        embeddings = self.embedding_model.encode(
            texts,
            batch_size=self.config.batch_size,
            show_progress_bar=len(texts) > 10
        )
        return embeddings.tolist()
    
    def add_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Add document chunks to the vector store.
        
        Args:
            chunks: List of DocumentChunk objects to add.
        
        Returns:
            int: Number of chunks added.
        """
        if not chunks:
            return 0
        
        # Extract text content
        texts = [chunk.content for chunk in chunks]
        ids = [chunk.id for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts)
        
        # Prepare metadata
        metadatas = [
            {
                "source": chunk.source,
                "chunk_index": chunk.chunk_index,
                **{k: str(v) for k, v in chunk.metadata.items()}
            }
            for chunk in chunks
        ]
        
        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        
        return len(chunks)
    
    def add_document(self, document: ProcessedDocument) -> int:
        """Add a processed document to the vector store.
        
        Args:
            document: The ProcessedDocument to add.
        
        Returns:
            int: Number of chunks added.
        """
        return self.add_chunks(document.chunks)
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[dict] = None
    ) -> list[dict]:
        """Search the knowledge base.
        
        Args:
            query: The search query.
            n_results: Number of results to return.
            filter_metadata: Optional metadata filters.
        
        Returns:
            list: List of search results with content and metadata.
        """
        # Generate query embedding
        query_embedding = self.generate_embeddings([query])[0]
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
        )
        
        # Format results
        formatted = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                    "id": results["ids"][0][i] if results["ids"] else None
                })
        
        return formatted
    
    def get_stats(self) -> dict:
        """Get statistics about the knowledge base.
        
        Returns:
            dict: Statistics including count of documents.
        """
        return {
            "collection_name": self.config.collection_name,
            "total_chunks": self.collection.count(),
            "embedding_model": self.config.model_name,
        }


# Default pipeline instance
_default_pipeline: Optional[EmbeddingPipeline] = None


def get_pipeline() -> EmbeddingPipeline:
    """Get or create the default embedding pipeline.
    
    Returns:
        EmbeddingPipeline: The default pipeline instance.
    """
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = EmbeddingPipeline()
    return _default_pipeline
