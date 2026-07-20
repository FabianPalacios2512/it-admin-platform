import asyncio
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.server import ServerConfig
from app.services.monitoring_service import get_server_stats, get_cached_monitoring_stats, sync_monitoring_stats

router = APIRouter(tags=["Monitoring"])

@router.get("/")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    try:
        results = get_cached_monitoring_stats()
        
        # If cache is totally empty (e.g. just restarted and first poll hasn't finished)
        if not results:
            # We trigger one sync asynchronously in background or let the scheduler handle it,
            # but to not leave UI empty, we could do a direct fetch or just return empty.
            # Returning empty is safer so we never block. The UI handles empty arrays.
            pass
            
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
