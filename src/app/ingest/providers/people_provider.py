"""Google People Provider - Fetch contacts from Google People API."""

import logging
import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class PeopleProvider:
    """Provider for fetching contacts from Google People API."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/contacts.readonly',
        'https://www.googleapis.com/auth/user.addresses.read',
        'https://www.googleapis.com/auth/user.emails.read',
        'https://www.googleapis.com/auth/user.phonenumbers.read'
    ]
    
    # Path setup similar to Drive provider
    _project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    credentials_path = _project_root / "credentials.json"
    token_path = _project_root / "token_people.pickle" # Separate token for now to avoid conflict/overwrite issues
    
    def __init__(self):
        self.creds = None
        self.service = None
        
    def authenticate(self):
        """Authenticate with Google People API."""
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)
                
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), self.SCOPES)
                self.creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)
                
        self.service = build('people', 'v1', credentials=self.creds)
        logger.info("Successfully authenticated with Google People API")
        
    def fetch_contacts(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch connections from People API."""
        if not self.service:
            self.authenticate()
            
        results = []
        page_token = None
        
        while True:
            # Request specific fields to be efficient
            req = self.service.people().connections().list(
                resourceName='people/me',
                pageSize=100, # Max allowed is 1000, keep smaller for safety
                personFields='names,emailAddresses,addresses,photos,phoneNumbers',
                pageToken=page_token
            )
            data = req.execute()
            connections = data.get('connections', [])
            
            for person in connections:
                contact = self._parse_person(person)
                if contact:
                    results.append(contact)
                    
            page_token = data.get('nextPageToken')
            if not page_token or len(results) >= limit:
                break
                
        return results
        
    def _parse_person(self, person: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract relevant fields from person object."""
        names = person.get('names', [])
        if not names:
            return None
            
        name = names[0].get('displayName')
        
        emails = [e.get('value') for e in person.get('emailAddresses', [])]
        phones = [p.get('value') for p in person.get('phoneNumbers', [])]
        
        # Get addresses
        addresses = []
        for addr in person.get('addresses', []):
            formatted = addr.get('formattedValue')
            if formatted:
                addresses.append({
                    'formatted': formatted,
                    'city': addr.get('city'),
                    'street': addr.get('streetAddress'),
                    'region': addr.get('region'),
                    'country': addr.get('country')
                })
                
        # Get photo
        photos = person.get('photos', [])
        photo_url = photos[0].get('url') if photos else None
                
        return {
            'resourceName': person.get('resourceName'),
            'name': name,
            'emails': emails,
            'phones': phones,
            'addresses': addresses,
            'photoUrl': photo_url
        }
