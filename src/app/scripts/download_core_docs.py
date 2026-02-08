"""Download core documents from Google Drive."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.ingest.providers.google_drive_provider import GoogleDriveProvider

def main():
    provider = GoogleDriveProvider()
    output_dir = Path("data/core_documents")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download Resume
    print("Searching for Resume...")
    results = provider.search_files(
        query="name contains 'Resume_36' and trashed = false", 
        limit=1
    )
    if results:
        file_info = results[0]
        print(f"Found: {file_info['name']}")
        content = provider.download_file(file_info['id'], file_info['mimeType'])
        out_path = output_dir / "Resume.txt"
        out_path.write_text(content, encoding='utf-8')
        print(f"Saved Resume: {len(content)} chars to {out_path}")
    else:
        print("Resume not found!")
    
    # Download The Book
    print("\nSearching for The Book...")
    results = provider.search_files(
        query="name contains 'The Book' and trashed = false", 
        limit=5
    )
    if results:
        for r in results:
            print(f"  - {r['name']} (modified: {r.get('modifiedTime', 'unknown')})")
        
        # Filter out 'Business Book' if user wants broader 'The Book'
        book_candidates = [r for r in results if 'Business' not in r['name']]
        if not book_candidates:
            book_candidates = results
        
        file_info = book_candidates[0]
        print(f"\nDownloading: {file_info['name']}")
        content = provider.download_file(file_info['id'], file_info['mimeType'])
        out_path = output_dir / "TheBook.txt"
        out_path.write_text(content, encoding='utf-8')
        print(f"Saved The Book: {len(content)} chars to {out_path}")
    else:
        print("The Book not found!")
    
    print("\n=== Done ===")
    print(f"Files saved to: {output_dir.absolute()}")

if __name__ == "__main__":
    main()
