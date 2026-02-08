"""End-to-End Tests for Document Ingestion and RAG Features.

This test suite validates:
1. DocumentExtractor - PDF, DOCX, text extraction
2. EmbeddingPipeline - ChromaDB storage and retrieval
3. Core Documents - Resume and The Book ingestion
4. Health Documents - PDF extraction and ingestion
5. RAGEngine - Context retrieval and response generation

Run with: pytest tests/test_e2e_ingestion.py -v
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


class TestDocumentExtractor:
    """Tests for the DocumentExtractor utility."""
    
    def test_extractor_initialization(self):
        """Test DocumentExtractor initializes with available backends."""
        from src.app.ingest.document_extractor import DocumentExtractor
        
        extractor = DocumentExtractor()
        
        # pypdf should be available (we installed it)
        assert extractor._pypdf_available is True
        
        # python-docx should be available
        assert extractor._docx_available is True
    
    def test_extract_text_file(self, tmp_path):
        """Test extraction from plain text files."""
        from src.app.ingest.document_extractor import DocumentExtractor
        
        # Create test text file
        test_file = tmp_path / "test.txt"
        test_content = "This is a test document.\nWith multiple lines."
        test_file.write_text(test_content)
        
        extractor = DocumentExtractor()
        result = extractor.extract_from_file(test_file)
        
        assert result.success is True
        assert result.content == test_content
        assert result.format == "text"
    
    def test_extract_pdf_bytes(self):
        """Test PDF extraction handles bytes input."""
        from src.app.ingest.document_extractor import DocumentExtractor
        
        extractor = DocumentExtractor()
        
        # Test with invalid bytes (should fail gracefully)
        result = extractor.extract_from_bytes(b"not a pdf", "pdf", "test.pdf")
        
        assert result.success is False
        assert result.error is not None
    
    def test_extractor_handles_missing_file(self):
        """Test graceful handling of missing files."""
        from src.app.ingest.document_extractor import DocumentExtractor
        
        extractor = DocumentExtractor()
        result = extractor.extract_from_file("/nonexistent/file.pdf")
        
        assert result.success is False
        assert "not found" in result.error.lower()
    
    def test_extractor_handles_unsupported_format(self, tmp_path):
        """Test unsupported file formats are rejected."""
        from src.app.ingest.document_extractor import DocumentExtractor
        
        test_file = tmp_path / "test.xyz"
        test_file.write_text("content")
        
        extractor = DocumentExtractor()
        result = extractor.extract_from_file(test_file)
        
        assert result.success is False
        assert "unsupported" in result.error.lower()


class TestEmbeddingPipeline:
    """Tests for the EmbeddingPipeline and ChromaDB integration."""
    
    def test_pipeline_initialization(self):
        """Test EmbeddingPipeline initializes correctly."""
        from src.app.ingest.embedding_pipeline import EmbeddingPipeline, EmbeddingConfig
        
        config = EmbeddingConfig(
            persist_directory="data/test_chroma",
            collection_name="test_collection"
        )
        pipeline = EmbeddingPipeline(config)
        
        assert pipeline.config.collection_name == "test_collection"
    
    def test_embedding_generation(self):
        """Test embedding vector generation."""
        from src.app.ingest.embedding_pipeline import EmbeddingPipeline
        
        pipeline = EmbeddingPipeline()
        
        texts = ["Hello world", "This is a test"]
        embeddings = pipeline.generate_embeddings(texts)
        
        assert len(embeddings) == 2
        assert len(embeddings[0]) > 0  # Embedding should have dimensions
        assert isinstance(embeddings[0], list)
    
    def test_add_and_search_chunks(self):
        """Test adding chunks and searching for them."""
        from src.app.ingest.embedding_pipeline import EmbeddingPipeline, EmbeddingConfig
        from src.app.ingest.document_processor import DocumentChunk
        import uuid
        
        config = EmbeddingConfig(
            persist_directory="data/test_chroma_search",
            collection_name=f"test_search_{uuid.uuid4().hex[:8]}"
        )
        pipeline = EmbeddingPipeline(config)
        
        # Create test chunks
        chunks = [
            DocumentChunk(
                content=content,
                source="test_source",
                chunk_index=i,
                metadata={"source": "test"}
            )
            for i, content in enumerate([
                "The quick brown fox jumps over the lazy dog.",
                "Machine learning is a subset of artificial intelligence.",
                "Python is a popular programming language."
            ])
        ]
        
        # Add chunks
        added = pipeline.add_chunks(chunks)
        assert added == 3
        
        # Search for relevant content
        results = pipeline.search("artificial intelligence", n_results=2)
        
        assert len(results) > 0
        # ML chunk should be most relevant
        assert "machine learning" in results[0]['content'].lower() or \
               "artificial intelligence" in results[0]['content'].lower()


class TestCoreDocumentsIngestion:
    """Tests for core documents (Resume, The Book) ingestion."""
    
    def test_resume_exists(self):
        """Verify Resume.txt was downloaded and has content."""
        resume_path = Path("data/core_documents/Resume.txt")
        
        assert resume_path.exists(), "Resume.txt not found"
        
        content = resume_path.read_text(encoding='utf-8')
        assert len(content) > 1000, "Resume content too short"
        
        # Verify key content
        assert "JARED COHEN" in content or "jared" in content.lower()
        assert "CFA" in content or "finance" in content.lower()
    
    def test_the_book_exists(self):
        """Verify TheBook.txt was downloaded and has content."""
        book_path = Path("data/core_documents/TheBook.txt")
        
        assert book_path.exists(), "TheBook.txt not found"
        
        content = book_path.read_text(encoding='utf-8')
        assert len(content) > 50000, "The Book content too short"
        
        # Verify philosophical content indicators
        assert "chaos" in content.lower() or "theory" in content.lower()
    
    def test_core_docs_in_rag(self):
        """Verify core documents are searchable in RAG."""
        from src.app.ingest.embedding_pipeline import get_pipeline
        
        pipeline = get_pipeline()
        
        # Search for resume content
        results = pipeline.search("CFA Charterholder finance experience", n_results=3)
        
        # Should find relevant chunks
        assert len(results) > 0
        
        # At least one result should be from core documents
        found_core = any(
            'core' in r.get('metadata', {}).get('source', '').lower() or
            'resume' in r.get('metadata', {}).get('source_name', '').lower()
            for r in results
        )
        # This may fail if metadata wasn't set, but content should match
        content_match = any(
            'cfa' in r.get('content', '').lower() or
            'investment' in r.get('content', '').lower()
            for r in results
        )
        
        assert found_core or content_match, "Core document content not found in RAG"


class TestHealthDocumentsIngestion:
    """Tests for health documents extraction and ingestion."""
    
    def test_health_documents_exist(self):
        """Verify health documents were extracted."""
        health_dir = Path("data/health_documents")
        
        assert health_dir.exists(), "Health documents directory not found"
        
        # Should have some .txt files
        txt_files = list(health_dir.rglob("*.txt"))
        assert len(txt_files) > 0, "No health text files found"
    
    def test_health_docs_in_rag(self):
        """Verify health documents are searchable in RAG."""
        from src.app.ingest.embedding_pipeline import get_pipeline
        
        pipeline = get_pipeline()
        
        # Search for health-related content
        results = pipeline.search("medical health vision", n_results=5)
        
        # Should find relevant chunks
        assert len(results) > 0
        
        # Check if any result is health-related
        health_found = any(
            'health' in r.get('metadata', {}).get('document_type', '').lower() or
            'health' in r.get('metadata', {}).get('source', '').lower() or
            'medical' in r.get('content', '').lower() or
            'vision' in r.get('content', '').lower()
            for r in results
        )
        
        assert health_found, "Health document content not found in RAG"


class TestRAGEngine:
    """Tests for the RAG Engine integration."""
    
    def test_rag_engine_initialization(self):
        """Test RAGEngine initializes correctly."""
        from src.app.rag.engine import RAGEngine
        
        engine = RAGEngine()
        
        assert engine.embedding_pipeline is not None
        assert engine.slm is not None
    
    def test_rag_context_retrieval(self):
        """Test RAG retrieves relevant context."""
        from src.app.rag.engine import RAGEngine
        
        engine = RAGEngine()
        
        # This tests the retrieval part (not generation, to avoid LLM dependency)
        results = engine.embedding_pipeline.search("professional experience investment", n_results=3)
        
        assert len(results) > 0
        assert all('content' in r for r in results)


class TestRAGStats:
    """Tests verifying RAG collection statistics."""
    
    def test_rag_has_expected_chunks(self):
        """Verify RAG has the expected number of chunks."""
        from src.app.ingest.embedding_pipeline import get_pipeline
        
        pipeline = get_pipeline()
        stats = pipeline.get_stats()
        
        # We should have at least the core + health documents
        # Core: ~555 chunks, Health: ~63 chunks = ~618 total
        assert stats['total_chunks'] >= 500, f"Expected at least 500 chunks, got {stats['total_chunks']}"
        
        print(f"\n📊 RAG Stats: {stats['total_chunks']} total chunks")


class TestEndToEndFlow:
    """Full end-to-end flow tests."""
    
    def test_document_to_rag_flow(self, tmp_path):
        """Test complete flow: document -> extraction -> embedding -> search."""
        from src.app.ingest.document_extractor import DocumentExtractor
        from src.app.ingest.document_processor import DocumentProcessor
        from src.app.ingest.embedding_pipeline import EmbeddingPipeline, EmbeddingConfig
        import uuid
        
        # Create test document
        test_file = tmp_path / "test_doc.txt"
        test_content = """
        This is an E2E test document about machine learning.
        It covers topics like neural networks and deep learning.
        The document discusses artificial intelligence applications.
        """
        test_file.write_text(test_content)
        
        # 1. Extract content
        extractor = DocumentExtractor()
        extraction_result = extractor.extract_from_file(test_file)
        assert extraction_result.success
        
        # 2. Process into chunks
        processor = DocumentProcessor()
        processed = processor.process_text(extraction_result.content, "test_doc.txt")
        assert len(processed.chunks) > 0
        
        # 3. Add to fresh collection
        config = EmbeddingConfig(
            persist_directory="data/test_chroma_e2e",
            collection_name=f"e2e_test_{uuid.uuid4().hex[:8]}"
        )
        pipeline = EmbeddingPipeline(config)
        
        added = pipeline.add_document(processed)
        assert added > 0
        
        # 4. Search and verify
        results = pipeline.search("neural networks deep learning", n_results=3)
        assert len(results) > 0
        
        # Verify content relevance
        found_ml_content = any(
            'machine learning' in r['content'].lower() or
            'neural' in r['content'].lower()
            for r in results
        )
        assert found_ml_content, "Expected ML content not found in search results"
        
        print("\n✅ E2E flow test passed: Document -> Extract -> Embed -> Search")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
