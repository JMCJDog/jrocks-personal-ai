"""Search for contacts files in Google Drive."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, '.')

from src.app.features.drive_search import search_drive, format_drive_results

def main():
    print("Searching for contacts files...")
    # Search for common contact export formats
    queries = [
        "contacts.vcf",
        "contacts.csv",
        "Google Contacts",
        "connections.csv"
    ]
    
    found_any = False
    for query in queries:
        print(f"\n--- Searching for: {query} ---")
        results = search_drive(query)
        if results:
            found_any = True
            print(format_drive_results(results))
        else:
            print("No results found.")
            
    if not found_any:
        print("\nNo contact files found in Drive. Will likely need to use People API.")

if __name__ == "__main__":
    main()
