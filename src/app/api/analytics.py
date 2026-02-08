"""Analytics API Router."""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from ..services.contacts_service import ContactsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/heatmap", response_model=List[Dict[str, Any]])
async def get_heatmap_data(
    force_refresh: bool = False,
    include_history: bool = Query(True, description="Include Google Location History")
):
    """Get weighted location data for heatmap.
    
    Combines:
    1. Google Contacts (High weight)
    2. Location History (aggregated density)
    """
    results = []
    
    # 1. Fetch Contacts
    try:
        service = ContactsService()
        contacts = service.get_contacts_with_location(force_refresh=force_refresh)
        # Add source info
        for c in contacts:
            c["source"] = "contact"
            c["weight"] = 5.0 # High prominence
        results.extend(contacts)
    except Exception as e:
        print(f"Error fetching contacts: {e}")

    # 2. Fetch Location History (Aggregated)
    if include_history:
        try:
            import sqlite3
            import os
            
            db_path = "data/locations.db"
            if os.path.exists(db_path):
                with sqlite3.connect(db_path) as conn:
                    # Aggregate to ~1km grid (2 decimal places)
                    cursor = conn.execute("""
                        SELECT 
                            CAST(lat * 100 AS INTEGER) / 100.0 as grid_lat,
                            CAST(lng * 100 AS INTEGER) / 100.0 as grid_lng,
                            COUNT(*) as intensity
                        FROM locations
                        GROUP BY grid_lat, grid_lng
                        ORDER BY intensity DESC
                        LIMIT 2000
                    """)
                    
                    rows = cursor.fetchall()
                    
                    # Normalize intensity 0-1? Or just use raw count?
                    # Leaflet heatmap usually likes 0-1 or counts.
                    # We'll calculate max for normalization.
                    max_intensity = rows[0][2] if rows else 1
                    
                    for row in rows:
                        lat, lng, count = row
                        normalized = min((count / max_intensity) * 3, 3.0) # Cap at 3.0 weight
                        results.append({
                            "lat": lat,
                            "lng": lng,
                            "weight": normalized,
                            "name": f"History Density ({count} pts)",
                            "address": "Frequent Location",
                            "source": "history"
                        })
        except Exception as e:
            print(f"Error fetching location history: {e}")

    return results
