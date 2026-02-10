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
import time

from ..document_processor import DocumentProcessor, ProcessedDocument
from ..drive_metadata_db import DriveMetadataDB

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
        self.db = DriveMetadataDB()
    
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

    def _retry_operation(self, func, *args, **kwargs):
        """Retry an operation with exponential backoff."""
        max_retries = 5
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (ConnectionError, OSError) as e:
                # Handle connection reset errors (WinError 10054, 10053)
                if attempt == max_retries - 1:
                    logger.error(f"Operation failed after {max_retries} attempts: {e}")
                    raise
                
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Operation failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {delay}s...")
                time.sleep(delay)
            except Exception as e:
                # Re-raise other exceptions immediately
                raise e



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
        def _search():
            if not self.service:
                self.authenticate()
                
            results = self.service.files().list(
                q=query,
                pageSize=limit,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, description)"
            ).execute()
            return results.get('files', [])

        return self._retry_operation(_search)

    def download_file(self, file_id: str, mime_type: str) -> str:
        """Download or export a file's content.
        
        Args:
            file_id: The Drive file ID.
            mime_type: The source MIME type.
            
        Returns:
            Extracted text content.
        """
        def _download():
            if not self.service:
                self.authenticate()
                
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
            if mime_type == 'application/vnd.google-apps.document':
                # Text usually comes with BOM
                return raw_content.decode('utf-8-sig')
            else:
                # Fallback for others
                try:
                    return raw_content.decode('utf-8')
                except:
                    return f"[Binary Content: {len(raw_content)} bytes]"

        return self._retry_operation(_download)

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

    def crawl_and_index(self) -> dict[str, int]:
        """Recursively crawl all files and index metadata to SQLite.
        
        Returns:
            Stats dict {"indexed": count, "errors": count}
        """
        if not self.service:
            self.authenticate()
            
        logger.info("Starting Google Drive crawl...")
        stats = {"indexed": 0, "errors": 0}
        
        try:
            # 1. Fetch ALL files (pages)
            # We fetch a simplified list first to build the tree
            page_token = None
            all_files = []
            
            while True:
                response = self.service.files().list(
                    q="trashed = false",
                    spaces='drive',
                    fields="nextPageToken, files(id, name, mimeType, parents, modifiedTime, description, starred, size)",
                    pageSize=1000,
                    pageToken=page_token
                ).execute()
                
                files = response.get('files', [])
                all_files.extend(files)
                stats["indexed"] += len(files)
                print(f"Fetched {len(all_files)} files so far...")
                
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
            
            # 2. Build Path Map
            # id -> {name, parent_id}
            file_map = {f['id']: f for f in all_files}
            
            # Helper to resolve path
            def get_path(file_id: str) -> str:
                path_parts = []
                current_id = file_id
                
                # Prevent infinite loops with depth limit
                depth = 0
                while current_id in file_map and depth < 20:
                    f = file_map[current_id]
                    path_parts.insert(0, f['name'])
                    
                    parents = f.get('parents', [])
                    if not parents:
                        break
                    current_id = parents[0] # Just take first parent
                    depth += 1
                    
                return "/" + "/".join(path_parts)

            # 3. Index to DB
            logger.info("Saving metadata to database...")
            for f in all_files:
                try:
                    # Enrich with computed path
                    f['path'] = get_path(f['id'])
                    self.db.upsert_file(f)
                except Exception as e:
                    logger.error(f"Error indexing file {f.get('name')}: {e}")
                    stats["errors"] += 1
            
            logger.info(f"Drive crawl complete. Stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            raise

