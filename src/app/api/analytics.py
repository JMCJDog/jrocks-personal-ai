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

@router.get("/health", response_model=Dict[str, Any])
async def get_system_health():
    """Get system health status."""
    import psutil
    import time
    
    # Mock database check (replace with real check)
    db_status = "connected" 
    
    # Mock MCP check
    mcp_status = "operational"

    return {
        "uptime": time.time() - psutil.boot_time(), # System uptime
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "database": db_status,
        "mcp_server": mcp_status,
        "status": "healthy"
    }

@router.get("/usage", response_model=Dict[str, Any])
async def get_model_usage():
    """Get model usage metrics."""
    # This would ideally come from a database tracking usage
    return {
        "daily_tokens": 15420,
        "monthly_tokens": 342000,
        "estimated_cost": 4.52, # USD
        "top_models": [
            {"name": "llama3.2", "count": 1200},
            {"name": "gpt-4o", "count": 4500},
            {"name": "claude-3-5-sonnet", "count": 2800}
        ]
    }

@router.get("/freshness", response_model=List[Dict[str, Any]])
async def get_data_freshness():
    """Check freshness of key data sources."""
    import os
    from datetime import datetime
    
    data_sources = [
        {"name": "Google Photos", "path": "data/google_photos_meta.json", "expected_freq": 7},
        {"name": "Chat History", "path": "data/chat_history.db", "expected_freq": 1},
        {"name": "Location History", "path": "data/locations.db", "expected_freq": 30}
    ]
    
    results = []
    for source in data_sources:
        status = "unknown"
        last_updated = None
        days_ago = None
        
        if os.path.exists(source["path"]):
            mtime = os.path.getmtime(source["path"])
            last_updated = datetime.fromtimestamp(mtime).isoformat()
            days_ago = (datetime.now() - datetime.fromtimestamp(mtime)).days
            
            if days_ago <= source["expected_freq"]:
                status = "fresh"
            elif days_ago <= source["expected_freq"] * 2:
                status = "stale"
            else:
                status = "outdated"
        else:
            status = "missing"
            
        results.append({
            "name": source["name"],
            "status": status,
            "last_updated": last_updated,
            "days_ago": days_ago
        })
        
    return results

@router.get("/code-stats", response_model=Dict[str, Any])
async def get_code_stats():
    """Get code quality and complexity stats."""
    # In a real implementation, we might run `radon` or `scc` here
    # For now, we'll return mocked data or basic counts
    import os
    
    total_loc = 0
    py_files = 0
    ts_files = 0
    
    root_dir = "."
    for root, dirs, files in os.walk(root_dir):
        if "node_modules" in root or ".venv" in root or ".git" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                py_files += 1
                # simplistic LOC count
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        total_loc += sum(1 for line in f if line.strip())
                except: pass
            elif file.endswith(".ts") or file.endswith(".tsx"):
                ts_files += 1
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        total_loc += sum(1 for line in f if line.strip())
                except: pass

    return {
        "lines_of_code": total_loc,
        "python_files": py_files,
        "typescript_files": ts_files,
        "complexity_score": "B+", # Placeholder
        "durability_score": 85 # Placeholder
    }

