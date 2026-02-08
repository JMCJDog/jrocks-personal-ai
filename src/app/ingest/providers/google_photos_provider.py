"""Google Photos Provider - Access and download photos from Google Photos.

Supports OAuth authentication with the Google Photos Library API and provides
methods to list, search, and download photos for local processing.
"""

import io
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GooglePhotosProvider:
    """Provider for accessing Google Photos Library.
    
    Handles:
    - OAuth 2.0 authentication with Google Photos scope
    - Listing media items and albums
    - Downloading photos for local analysis
    - Date-range filtering for photo searches
    
    Example:
        >>> provider = GooglePhotosProvider()
        >>> provider.authenticate()
        >>> photos = provider.list_photos(max_results=50)
    """
    
    # Combined scopes for Drive + Photos access
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/photoslibrary.readonly',
    ]
    
    # Resolve paths relative to project root
    _project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    
    credentials_path = _project_root / "credentials.json"
    token_path = _project_root / "token_photos.pickle"  # Separate token for Photos
    cache_dir = _project_root / "data" / "photos_cache"
    
    def __init__(self) -> None:
        """Initialize the Google Photos provider."""
        self.creds = None
        self.service = None
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def authenticate(self) -> None:
        """Authenticate with Google Photos using OAuth 2.0.
        
        Loads saved credentials or triggers the auth flow.
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
        
        self.service = build('photoslibrary', 'v1', credentials=self.creds,
                             static_discovery=False)
        logger.info("Successfully authenticated with Google Photos")

    def list_photos(
        self, 
        max_results: int = 100,
        page_token: Optional[str] = None
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        """List photos from the user's library.
        
        Args:
            max_results: Maximum number of photos to return (max 100 per call).
            page_token: Token for pagination.
            
        Returns:
            Tuple of (list of media items, next page token).
        """
        if not self.service:
            self.authenticate()
        
        try:
            results = self.service.mediaItems().list(
                pageSize=min(max_results, 100),
                pageToken=page_token
            ).execute()
            
            items = results.get('mediaItems', [])
            next_token = results.get('nextPageToken')
            
            logger.info(f"Retrieved {len(items)} photos from Google Photos")
            return items, next_token
            
        except Exception as e:
            logger.error(f"Error listing photos: {e}")
            raise

    def search_by_date_range(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        max_results: int = 100
    ) -> list[dict[str, Any]]:
        """Search for photos within a date range.
        
        Args:
            start_date: Start of date range.
            end_date: End of date range (defaults to now).
            max_results: Maximum photos to return.
            
        Returns:
            List of media items matching the date range.
        """
        if not self.service:
            self.authenticate()
        
        end_date = end_date or datetime.now()
        
        # Build date filter
        filters = {
            "dateFilter": {
                "ranges": [{
                    "startDate": {
                        "year": start_date.year,
                        "month": start_date.month,
                        "day": start_date.day
                    },
                    "endDate": {
                        "year": end_date.year,
                        "month": end_date.month,
                        "day": end_date.day
                    }
                }]
            }
        }
        
        try:
            all_items = []
            page_token = None
            
            while len(all_items) < max_results:
                body = {
                    "pageSize": min(100, max_results - len(all_items)),
                    "filters": filters
                }
                if page_token:
                    body["pageToken"] = page_token
                
                results = self.service.mediaItems().search(body=body).execute()
                items = results.get('mediaItems', [])
                all_items.extend(items)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(all_items)} photos in date range")
            return all_items
            
        except Exception as e:
            logger.error(f"Error searching photos: {e}")
            raise

    def search_last_n_days(self, days: int, max_results: int = 100) -> list[dict[str, Any]]:
        """Search for photos from the last N days.
        
        Args:
            days: Number of days to look back.
            max_results: Maximum photos to return.
            
        Returns:
            List of media items from the specified period.
        """
        start_date = datetime.now() - timedelta(days=days)
        return self.search_by_date_range(start_date, max_results=max_results)

    def download_photo(
        self, 
        media_item: dict[str, Any],
        max_width: int = 1024,
        max_height: int = 1024
    ) -> Optional[Path]:
        """Download a photo to local cache.
        
        Args:
            media_item: Media item metadata from list/search.
            max_width: Maximum width for download.
            max_height: Maximum height for download.
            
        Returns:
            Path to downloaded file, or None if failed.
        """
        try:
            item_id = media_item['id']
            filename = media_item.get('filename', f"{item_id}.jpg")
            cache_path = self.cache_dir / filename
            
            # Check cache first
            if cache_path.exists():
                logger.debug(f"Using cached photo: {filename}")
                return cache_path
            
            # Build download URL with size parameters
            base_url = media_item['baseUrl']
            download_url = f"{base_url}=w{max_width}-h{max_height}"
            
            # Download using requests (googleapiclient doesn't handle this well)
            import requests
            response = requests.get(download_url)
            response.raise_for_status()
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded photo: {filename}")
            return cache_path
            
        except Exception as e:
            logger.error(f"Error downloading photo: {e}")
            return None

    def list_albums(self, max_results: int = 50) -> list[dict[str, Any]]:
        """List user's photo albums.
        
        Args:
            max_results: Maximum albums to return.
            
        Returns:
            List of album metadata.
        """
        if not self.service:
            self.authenticate()
        
        try:
            results = self.service.albums().list(
                pageSize=min(max_results, 50)
            ).execute()
            
            albums = results.get('albums', [])
            logger.info(f"Found {len(albums)} albums")
            return albums
            
        except Exception as e:
            logger.error(f"Error listing albums: {e}")
            raise

    def get_album_photos(
        self, 
        album_id: str, 
        max_results: int = 100
    ) -> list[dict[str, Any]]:
        """Get photos from a specific album.
        
        Args:
            album_id: The album ID.
            max_results: Maximum photos to return.
            
        Returns:
            List of media items in the album.
        """
        if not self.service:
            self.authenticate()
        
        try:
            all_items = []
            page_token = None
            
            while len(all_items) < max_results:
                body = {
                    "albumId": album_id,
                    "pageSize": min(100, max_results - len(all_items))
                }
                if page_token:
                    body["pageToken"] = page_token
                
                results = self.service.mediaItems().search(body=body).execute()
                items = results.get('mediaItems', [])
                all_items.extend(items)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            return all_items
            
        except Exception as e:
            logger.error(f"Error getting album photos: {e}")
            raise
