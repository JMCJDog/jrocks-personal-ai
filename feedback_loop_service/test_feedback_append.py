
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from app.ingest.providers.google_drive_provider import GoogleDriveProvider

def main():
    print("Initializing provider...")
    provider = GoogleDriveProvider()
    
    doc_id = "1Gxv1doTBhDs7TGo8j9SncT4x_DbM_vDwcrIQ5xlUS-0"
    
    print(f"Appending Vibe Check to {doc_id}...")
    try:
        provider.append_text(doc_id, "\n\nVibe Check [Test]\n")
        print("Append successful!")
    except Exception as e:
        print(f"Append failed: {e}")

if __name__ == "__main__":
    main()
