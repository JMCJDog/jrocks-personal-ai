"""Contacts Service - Manage contact data and geocoding."""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from ..ingest.providers.people_provider import PeopleProvider

logger = logging.getLogger(__name__)

class ContactsService:
    """Service for managing contacts and location data."""
    
    _project_root = Path(__file__).resolve().parent.parent.parent.parent
    cache_path = _project_root / "data" / "contacts_cache.json"
    
    def __init__(self):
        self.provider = PeopleProvider()
        # Initialize geolocator with a unique user agent
        self.geolocator = Nominatim(user_agent="jrocks_personal_ai_analytics")
        # Rate limit to 1 request per second to be nice to Nominatim
        self.geocode = RateLimiter(self.geolocator.geocode, min_delay_seconds=1.0)
        
    def get_contacts_with_location(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get contacts with geocoded location data."""
        
        # unique key for cache validation could be added, but simple file existence for now
        if not force_refresh and self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    logger.info(f"Loaded {len(cached_data)} contacts from cache")
                    return cached_data
            except Exception as e:
                logger.error(f"Failed to load contact cache: {e}")
                
        # Fetch fresh contacts
        logger.info("Fetching fresh contacts from Google People API...")
        raw_contacts = self.provider.fetch_contacts(limit=2000)
        
        processed_contacts = []
        
        logger.info(f"Processing {len(raw_contacts)} contacts for location data...")
        
        for contact in raw_contacts:
            addresses = contact.get('addresses', [])
            if not addresses:
                continue
                
            # Use the first address
            address_obj = addresses[0]
            formatted_address = address_obj.get('formatted')
            
            if not formatted_address:
                continue
                
            # Geocode
            try:
                location = self.geocode(formatted_address)
                
                if location:
                    contact_data = {
                        'name': contact.get('name', 'Unknown'),
                        'address': formatted_address,
                        'email': contact.get('emails', [''])[0],
                        'lat': location.latitude,
                        'lng': location.longitude,
                        'weight': 1.0 # Default weight for heatmap
                    }
                    processed_contacts.append(contact_data)
                    logger.debug(f"Geocoded: {contact.get('name')} -> {location.latitude}, {location.longitude}")
                else:
                    logger.warning(f"Could not geocode address: {formatted_address}")
                    
            except Exception as e:
                logger.error(f"Error geocoding {formatted_address}: {e}")
                
        # Save to cache
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(processed_contacts, f, indent=2)
            logger.info(f"Saved {len(processed_contacts)} geocoded contacts to cache")
        except Exception as e:
            logger.error(f"Failed to save contact cache: {e}")
            
        return processed_contacts

# Global instance
_contacts_service = None

def get_contacts_service():
    global _contacts_service
    if _contacts_service is None:
        _contacts_service = ContactsService()
    return _contacts_service
