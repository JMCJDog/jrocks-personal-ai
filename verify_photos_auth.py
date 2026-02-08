"""Verify Google Photos API authentication.

Run this script after enabling the Google Photos Library API in Google Cloud Console.
It will trigger the OAuth flow and save credentials for the photo service.
"""

import sys
from pathlib import Path

# Add src to path
script_dir = Path(__file__).resolve().parent
sys.path.append(str(script_dir / "src"))

from app.ingest.providers.google_photos_provider import GooglePhotosProvider

def test_photos_auth():
    print("\n" + "="*50)
    print("Testing Google Photos Authentication")
    print("="*50)
    print("Initializing Provider...")
    
    try:
        provider = GooglePhotosProvider()
        
        print("\n[ACTION REQUIRED] A browser window should open for you to sign in.")
        print("Please grant access to your Google Photos library.")
        print("Waiting for authentication...\n")
        
        provider.authenticate()
        
        print("\n" + "="*50)
        print("SUCCESS! Authentication complete.")
        print(f"Token saved to: {provider.token_path.absolute()}")
        print("="*50 + "\n")
        
        # Test listing photos
        print("Testing photo listing...")
        photos, _ = provider.list_photos(max_results=5)
        print(f"Found {len(photos)} recent photos.")
        
        if photos:
            print("\nSample photo:")
            sample = photos[0]
            print(f"  - Filename: {sample.get('filename', 'N/A')}")
            print(f"  - ID: {sample.get('id', 'N/A')[:20]}...")
            print(f"  - MIME Type: {sample.get('mimeType', 'N/A')}")
        
        print("\n" + "="*50)
        print("Google Photos integration is working!")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"\nERROR: Authentication failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure Google Photos Library API is enabled at:")
        print("   https://console.cloud.google.com/apis/library/photoslibrary.googleapis.com")
        print("2. Make sure your account is added as a test user in OAuth consent screen")
        raise

if __name__ == "__main__":
    test_photos_auth()
