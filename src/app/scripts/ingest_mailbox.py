import logging
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.ingest.providers.mailbox_provider import MailboxProvider
from src.app.ingest.embedding_pipeline import get_pipeline

def main():
    parser = argparse.ArgumentParser(description="Ingest Gmail mbox file for RAG and Style.")
    parser.add_argument("mbox_path", help="Path to the .mbox file")
    parser.add_argument("--email", required=True, help="Your email address (to identify sent messages)")
    parser.add_argument("--limit", type=int, default=0, help="Max messages to process")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MailboxIngest")
    
    mbox_path = Path(args.mbox_path)
    if not mbox_path.exists():
        logger.error(f"File not found: {mbox_path}")
        return

    logger.info(f"Initializing ingestion for: {mbox_path}")
    logger.info(f"Targeting Sent Emails from: {args.email}")
    
    provider = MailboxProvider(str(mbox_path), user_email=args.email)
    pipeline = get_pipeline()
    
    style_corpus_path = Path("data/jrock_style_corpus.txt")
    style_corpus_path.parent.mkdir(parents=True, exist_ok=True)
    
    count = 0
    style_count = 0
    
    print("--- Starting Ingestion ---")
    
    try:
        # Open style file once
        with open(style_corpus_path, "a", encoding="utf-8") as f_style:
            
            for doc in provider.yield_documents(limit=args.limit):
                # 1. Index to RAG
                pipeline.add_document(doc)
                
                # 2. Extract Style (if sent by user)
                # metadata 'from' might be "Jared <jared@example.com>"
                from_header = doc.metadata.get("from", "").lower()
                if args.email.lower() in from_header:
                    f_style.write(f"--- Subject: {doc.metadata.get('subject')} ---\n")
                    f_style.write(doc.chunks[0].content if doc.chunks else "") 
                    # Note: doc.chunks[0].content might be partial if chunked. 
                    # But ProcessedDocument stores original text? No, it stores chunks.
                    # We should probably access the raw text from provider or reconstruct.
                    # For now, let's write all chunks joined.
                    full_text = "\n".join([c.content for c in doc.chunks])
                    f_style.write(full_text + "\n\n")
                    style_count += 1
                
                count += 1
                if count % 100 == 0:
                    print(f"Processed {count} emails... (Found {style_count} sent by you)")
                    
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        logger.exception("Ingestion failed")
        
    print(f"\n--- Complete ---")
    print(f"Total Processed: {count}")
    print(f"Style Examples Extracted: {style_count}")
    print(f"Style Corpus: {style_corpus_path}")

if __name__ == "__main__":
    main()
