import logging
import sys
from pathlib import Path

# Add project root to path so we can import src
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.ingest.providers.google_drive_provider import GoogleDriveProvider

def main():
    # Configure logging to show info
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        provider = GoogleDriveProvider()
        print("--- Google Drive Indexer ---")
        print("Authenticating and starting crawl...")
        
        # This will open a browser window if not authenticated
        stats = provider.crawl_and_index()
        
        print("\n--- Indexing Complete ---")
        print(f"Total Files Indexed: {stats['indexed']}")
        print(f"Errors Encountered: {stats['errors']}")
        print("Metadata saved to data/drive_index.db")
        
    except Exception as e:
        print(f"\nError: {e}")
        logging.exception("Indexing failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
