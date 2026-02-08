
import os
import pickle
import logging
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def check_drive():
    # Paths
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent # src/app/scripts -> src/app -> src -> project_root
    token_path = project_root / "token.pickle"
    creds_path = project_root / "credentials.json"
    
    print(f"Token path: {token_path}")
    
    creds = None
    if token_path.exists():
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                print("No credentials.json found.")
                return
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    
    print("Searching for Takeout files...")
    # Search for zip files with 'takeout' in name
    # Also sort by modifiedTime desc
    query = "name contains 'takeout' and mimeType = 'application/zip' and trashed = false"
    results = service.files().list(
        q=query,
        pageSize=10,
        orderBy="modifiedTime desc",
        fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)"
    ).execute()
    
    files = results.get('files', [])
    
    if not files:
        print("No Takeout files found.")
    else:
        print(f"Found {len(files)} Takeout files:")
        for f in files:
            print(f" - {f['name']} (ID: {f['id']}, Modified: {f.get('modifiedTime')}, Size: {f.get('size')})")

if __name__ == "__main__":
    check_drive()
