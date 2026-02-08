"""Ingest core documents into RAG vector store."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.ingest.document_processor import DocumentProcessor
from src.app.ingest.embedding_pipeline import EmbeddingPipeline

def main():
    print("=== Ingesting Core Documents into RAG ===")
    
    doc_processor = DocumentProcessor()
    pipeline = EmbeddingPipeline()
    
    core_docs_dir = Path("data/core_documents")
    
    # Files to ingest with their priorities
    files = [
        ("Resume.txt", "resume", 1.0),       # Highest priority
        ("TheBook.txt", "philosophy", 0.9),  # High priority
    ]
    
    for filename, doc_type, priority in files:
        filepath = core_docs_dir / filename
        if not filepath.exists():
            print(f"❌ {filename} not found!")
            continue
            
        print(f"\n📥 Processing: {filename}")
        content = filepath.read_text(encoding='utf-8')
        print(f"   Content length: {len(content)} chars")
        
        # Process into chunks
        processed = doc_processor.process_text(
            text=content,
            source_name=filename
        )
        
        # Add priority metadata to all chunks
        for chunk in processed.chunks:
            chunk.metadata['priority'] = priority
            chunk.metadata['document_type'] = doc_type
            chunk.metadata['source'] = 'core_persona'
        
        # Add to vector store
        chunks_added = pipeline.add_document(processed)
        print(f"   ✅ Added {chunks_added} chunks to vector store")
    
    # Print stats
    stats = pipeline.get_stats()
    print(f"\n=== RAG Stats ===")
    print(f"Total chunks in store: {stats['total_chunks']}")
    print("Done!")

if __name__ == "__main__":
    main()
