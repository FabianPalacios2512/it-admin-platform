"""
monitoring.py — API Endpoints de Monitoreo v2.0
================================================
GET  /api/v1/monitoring/              → Dashboard stats (desde caché)
GET  /api/v1/monitoring/{id}/processes → Top 5 procesos bajo demanda
"""
import asyncio
import concurrent.futures
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.models.server import ServerConfig
from app.services.monitoring_service import (
    get_cached_monitoring_stats,
    get_top_processes,
)

router = APIRouter(tags=["Monitoring"])

# Executor dedicado para tareas SSH/WMI bloqueantes en el endpoint de procesos
_processes_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)


@router.get("/")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Retorna métricas desde caché (actualizado por el scheduler). No bloquea."""
    try:
        results = get_cached_monitoring_stats()
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{server_id}/processes")
async def get_server_processes(server_id: int, db: Session = Depends(get_db)):
    """
    Obtiene el Top 5 de procesos del servidor bajo demanda.
    Timeout máximo de 12 segundos para no bloquear al usuario.
    """
    server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Servidor no encontrado.")

    loop = asyncio.get_event_loop()
    try:
        processes = await asyncio.wait_for(
            loop.run_in_executor(_processes_executor, get_top_processes, server),
            timeout=12.0
        )
        return {"success": True, "server_id": server_id, "processes": processes}
    except asyncio.TimeoutError:
        return {"success": False, "server_id": server_id, "processes": [], "error": "Timeout al obtener procesos (>12s)"}
    except Exception as e:
        return {"success": False, "server_id": server_id, "processes": [], "error": str(e)}
