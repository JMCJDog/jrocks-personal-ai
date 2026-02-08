from typing import List, Dict, Any
from src.app.ingest.drive_metadata_db import DriveMetadataDB

def search_drive(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search Google Drive metadata index.
    
    Args:
        query: Keyword to search for (name, path, description).
        limit: Max results.
        
    Returns:
        List of file metadata dictionaries.
    """
    db = DriveMetadataDB()
    return db.search_files(query, limit)

def format_drive_results(results: List[Dict[str, Any]]) -> str:
    """Format search results for display."""
    if not results:
        return "No files found matching your query."
        
    output = ["Found the following files in Google Drive:"]
    for f in results:
        icon = "📁" if f['mime_type'] == 'application/vnd.google-apps.folder' else "📄"
        output.append(f"{icon} **{f['name']}**")
        output.append(f"   Path: `{f['path']}`")
        if f['description']:
            output.append(f"   Note: {f['description']}")
        output.append(f"   Link: https://docs.google.com/open?id={f['id']}")
        output.append("")
        
    return "\n".join(output)
