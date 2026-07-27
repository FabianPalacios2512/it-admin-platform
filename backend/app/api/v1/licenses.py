from fastapi import APIRouter, Depends, HTTPException
from app.services.graph_service import graph_service

router = APIRouter()

@router.get("/inactive")
async def get_inactive_licenses(days: int = 90):
    """
    Retorna los usuarios que tienen licencias asignadas 
    pero que no han iniciado sesión en los últimos N días.
    """
    try:
        results = await graph_service.get_inactive_licensed_users(days_threshold=days)
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
