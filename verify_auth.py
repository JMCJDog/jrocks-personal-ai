import sys
from pathlib import Path
import logging

# Add src to path
# Since the script is in Projects/jrocks-personal-ai/, we need to add ./src logic
# Use __file__ relative path
script_dir = Path(__file__).resolve().parent
sys.path.append(str(script_dir / "src"))

from app.ingest.providers.google_drive_provider import GoogleDriveProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AuthTest")

def test_auth():
    print("\n" + "="*50)
    print("Testing Google Drive Authentication")
    print("="*50)
    print("Initializing Provider...")
    
    try:
        provider = GoogleDriveProvider()
        print("Provider initialized.")
        print("\n[ACTION REQUIRED] A browser window should open shortly for you to sign in.")
        print("Please log in with the account you added as a Test User.")
        print("Waiting for authentication...\n")
        
        provider.authenticate()
        
        print("\n" + "="*50)
        print("SUCCESS! Authentication complete.")
        print(f"Token saved to: {provider.token_path.absolute()}")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"\nERROR: Authentication failed: {e}")
        raise

if __name__ == "__main__":
    test_auth()
