"""Verify Google People API authentication."""
import sys
from pathlib import Path

# Add project root to path to allow imports
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.app.ingest.providers.people_provider import PeopleProvider

def main():
    print("=== Verifying People API Authentication ===")
    print("This will open a browser window to authenticate with Google.")
    print("Please grant the requested permissions (Contacts, Addresses).")
    
    provider = PeopleProvider()
    try:
        provider.authenticate()
        print("\n✅ Authentication successful!")
        print(f"Token saved to: {provider.token_path}")
        
        # Try fetching a few contacts to verify
        print("\nTesting API access...")
        contacts = provider.fetch_contacts(limit=5)
        print(f"✅ Successfully fetched {len(contacts)} contacts.")
        for contact in contacts:
            print(f" - {contact.get('name')} ({len(contact.get('addresses', []))} addresses)")
            
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
