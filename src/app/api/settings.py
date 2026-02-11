from fastapi import APIRouter, HTTPException
from ..core.settings import settings_manager, AppSettings

router = APIRouter(tags=["settings"])

@router.get("/", response_model=AppSettings)
async def get_settings():
    """Get current application settings."""
    try:
        return settings_manager.get()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=AppSettings)
async def update_settings(settings: AppSettings):
    """Update application settings."""
    try:
        settings_manager.save(settings)
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
