"""Download and ingest core persona documents from Google Drive.

Downloads specified files and adds them to the RAG vector store with high priority metadata.
"""
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.ingest.providers.google_drive_provider import GoogleDriveProvider
from src.app.ingest.document_processor import DocumentProcessor
from src.app.ingest.embedding_pipeline import get_pipeline

def main():
    print("=== Core Document Ingestion ===")
    
    # Initialize
    provider = GoogleDriveProvider()
    doc_processor = DocumentProcessor()
    pipeline = get_pipeline()
    
    # Target files - searching by name fragments
    target_files = [
        "Jared_Cohen_Resume_36",
        "The Book"  # Most recent version, broader than 'The Business Book'
    ]
    
    # Create output directory
    output_dir = Path("data/core_documents")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for query in target_files:
        print(f"\n📥 Searching for: {query}")
        
        # Search in Drive using Drive API query syntax
        drive_query = f"name contains '{query}' and trashed = false"
        results = provider.search_files(query=drive_query, limit=1)
        
        if not results:
            print(f"  ❌ Not found in Drive")
            continue
            
        file_info = results[0]
        file_id = file_info.get('id')
        file_name = file_info.get('name')
        mime_type = file_info.get('mimeType', '')
        
        print(f"  ✅ Found: {file_name} (ID: {file_id})")
        
        # Download
        output_path = output_dir / file_name
        
        # Handle Google Docs export
        if 'google-apps' in mime_type:
            # Export as plain text for processing
            print(f"  📄 Exporting Google Doc as text...")
            content = provider.download_file(file_id, mime_type)
            
            if content:
                # Save locally
                txt_path = output_dir / f"{Path(file_name).stem}.txt"
                txt_path.write_text(content, encoding='utf-8')
                print(f"  💾 Saved to: {txt_path}")
                
                # Process and embed
                print(f"  🧠 Indexing into RAG...")
                processed = doc_processor.process_text(
                    text=content,
                    source_name=file_name
                )
                
                # Add priority metadata
                for chunk in processed.chunks:
                    chunk.metadata['priority'] = 'high'
                    chunk.metadata['document_type'] = 'core_persona'
                    chunk.metadata['source_type'] = 'google_drive'
                
                chunks_added = pipeline.add_document(processed)
                print(f"  ✅ Added {chunks_added} chunks to vector store")
            else:
                print(f"  ❌ Failed to download content")
        else:
            # Binary file - download and process
            print(f"  📥 Downloading binary file...")
            content = provider.download_file(file_id, mime_type)
            if content:
                # Save as text since download_file returns string
                output_path = output_dir / f"{Path(file_name).stem}.txt"
                output_path.write_text(content, encoding='utf-8')
                print(f"  💾 Saved to: {output_path}")
                
                # Process based on file type
                processed = doc_processor.process_text(content, source_name=file_name)
                if processed:
                    for chunk in processed.chunks:
                        chunk.metadata['priority'] = 'high'
                        chunk.metadata['document_type'] = 'core_persona'
                    
                    chunks_added = pipeline.add_document(processed)
                    print(f"  ✅ Added {chunks_added} chunks to vector store")
    
    # Print stats
    stats = pipeline.get_stats()
    print(f"\n=== RAG Stats ===")
    print(f"Total chunks in store: {stats['total_chunks']}")
    print("Done!")

if __name__ == "__main__":
    main()
