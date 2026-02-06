"""Google Drive Provider - Index and ingest documents from Google Drive.

Supports indexing of Google Docs, Sheets, Slides, and PDF files.
Handles OAuth authentication and content export.
"""

import io
import logging
import os
import pickle
from pathlib import Path
from typing import Any, Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from ..document_processor import DocumentProcessor, ProcessedDocument

logger = logging.getLogger(__name__)


class GoogleDriveProvider:
    """Provider for indexing and ingesting Google Drive content.
    
    Handles:
    - User authentication via OAuth 2.0
    - File search and listing
    - Exporting Google Docs to text
    - Downloading PDFs and other files
    - Processing content into chunks
    
    Example:
        >>> provider = GoogleDriveProvider()
        >>> provider.authenticate()
        >>> docs = provider.index_folder("Memory/The Book")
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/documents', # For editing Docs
        'https://www.googleapis.com/auth/drive'      # General access
    ]
    
    # Resolve paths relative to project root
    # This file is in src/app/ingest/providers/
    # Root is up 5 levels? Let's verify:
    # src/app/ingest/providers/google_drive_provider.py
    # .parent -> providers
    # .parent -> ingest
    # .parent -> app
    # .parent -> src
    # .parent -> project_root
    _project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    
    credentials_path = _project_root / "credentials.json"
    token_path = _project_root / "token.pickle"
    
    # MIME types for export
    MIME_TYPES = {
        'application/vnd.google-apps.document': 'text/plain',
        'application/vnd.google-apps.spreadsheet': 'application/pdf', # Export to PDF then text extract? Or CSV
        'application/vnd.google-apps.presentation': 'text/plain',
    }
    
    def __init__(self, doc_processor: Optional[DocumentProcessor] = None) -> None:
        """Initialize the Google Drive provider.
        
        Args:
            doc_processor: Optional document processor instance.
        """
        self.doc_processor = doc_processor or DocumentProcessor()
        self.creds = None
        self.service = None
    
    def authenticate(self) -> None:
        """Authenticate with Google Drive using OAuth 2.0.
        
        Loads saved capabilities or triggers the auth flow.
        """
        if self.token_path.exists():
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        # Refresh or login if needed
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Missing {self.credentials_path}. "
                        "Download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)
        
        self.service = build('drive', 'v3', credentials=self.creds)
        logger.info("Successfully authenticated with Google Drive")

    def search_files(
        self, 
        query: str = "trashed = false", 
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Search for files in Google Drive.
        
        Args:
            query: Drive API query string.
            limit: Maximum files to return.
            
        Returns:
            List of file metadata objects.
        """
        if not self.service:
            self.authenticate()
            
        results = self.service.files().list(
            q=query,
            pageSize=limit,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, description)"
        ).execute()
        
        return results.get('files', [])

    def download_file(self, file_id: str, mime_type: str) -> str:
        """Download or export a file's content.
        
        Args:
            file_id: The Drive file ID.
            mime_type: The source MIME type.
            
        Returns:
            Extracted text content.
        """
        if not self.service:
            self.authenticate()
            
        content = ""
        
        try:
            # Handle Google Docs formats (Export)
            if mime_type in self.MIME_TYPES:
                export_mime = self.MIME_TYPES[mime_type]
                request = self.service.files().export_media(
                    fileId=file_id, mimeType=export_mime)
            
            # Handle binary files (Download)
            else:
                request = self.service.files().get_media(fileId=file_id)
            
            # Download content
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            fh.seek(0)
            raw_content = fh.read()
            
            # Convert to string for text types
            # For PDFs, this would need PDF processing logic integrated
            # Here for text/plain exports:
            if mime_type == 'application/vnd.google-apps.document':
                # Text usually comes with BOM
                content = raw_content.decode('utf-8-sig')
            else:
                # Fallback for others - might need specialized handlers
                try:
                    content = raw_content.decode('utf-8')
                except:
                    content = f"[Binary Content: {len(raw_content)} bytes]"
                    
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise
            
        return content

    def process_file(self, file_meta: dict[str, Any]) -> Optional[ProcessedDocument]:
        """Process a Drive file into a ProcessedDocument.
        
        Args:
            file_meta: File metadata from search.
            
        Returns:
            ProcessedDocument or None if failed.
        """
        file_id = file_meta['id']
        name = file_meta['name']
        mime_type = file_meta['mimeType']
        
        try:
            logger.info(f"Processing Drive file: {name} ({mime_type})")
            
            # Skip folders
            if mime_type == 'application/vnd.google-apps.folder':
                return None
            
            text_content = self.download_file(file_id, mime_type)
            
            if not text_content:
                return None
            
            # Use DocumentProcessor to chunk text
            doc = self.doc_processor.process_text(
                text=text_content,
                source_name=f"gdrive://{file_id}/{name}"
            )
            
            # Enrich metadata
            doc.title = name
            doc.metadata.update({
                "file_id": file_id,
                "drive_url": f"https://docs.google.com/document/d/{file_id}",
                "mime_type": mime_type,
                "modified_time": file_meta.get('modifiedTime'),
                "description": file_meta.get('description', '')
            })
            
            return doc
            
        except Exception as e:
            logger.error(f"Failed to process {name}: {e}")
            return None

    def index_specific_documents(self, specific_names: list[str]) -> list[ProcessedDocument]:
        """Index specific named documents (e.g., "The Book").
        
        Args:
            specific_names: List of exact document names to find.
            
        Returns:
            List of processed documents.
        """
        processed_docs = []
        
        for name in specific_names:
            # Escape single quotes in name
            safe_name = name.replace("'", "\\'")
            query = f"name = '{safe_name}' and trashed = false"
            
            files = self.search_files(query, limit=5)
            
            for f in files:
                doc = self.process_file(f)
                if doc:
                    processed_docs.append(doc)
                    
        return processed_docs

    def append_text(self, file_id: str, text: str) -> None:
        """Append text to the end of a Google Doc.
        
        Args:
            file_id: The Drive file ID.
            text: Text to append.
        """
        # Ensure we have credentials
        if not self.service:
            self.authenticate()
            
        try:
            # We need the docs service, not drive service, for edits
            # Note: We reuse the credentials
            docs_service = build('docs', 'v1', credentials=self.creds)
            
            # Get the document to find the end index
            doc = docs_service.documents().get(documentId=file_id).execute()
            content = doc.get('body').get('content')
            end_index = content[-1].get('endIndex') - 1
            
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': end_index,
                        },
                        'text': text
                    }
                }
            ]
            
            docs_service.documents().batchUpdate(
                documentId=file_id, 
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Appended text to doc {file_id}")
            
        except Exception as e:
            logger.error(f"Failed to append to doc {file_id}: {e}")
            raise
