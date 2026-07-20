from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import get_db
from app.models.server import ServerConfig
from app.models.rds import RdsConfig
from app.services.rds_service import get_rds_sessions, kill_rds_session, clean_temp_folder, execute_mass_cleanup, deploy_remote_task, query_remote_task, delete_remote_task

router = APIRouter(tags=["RDS"])

class ScheduleRequest(BaseModel):
    cron_time: str
    cron_days: str
    temp_path: str
    file_prefix: str = "Nova_est"

class KillRequest(BaseModel):
    session_id: Optional[str] = None
    username: Optional[str] = None
    temp_path: str = "C:\\conteo"
    file_prefix: str = "Nova_est"

@router.get("/sessions")
async def fetch_sessions(
    temp_path: Optional[str] = None,
    file_prefix: Optional[str] = None,
    db: Session = Depends(get_db)
):
    server = db.query(ServerConfig).filter(ServerConfig.server_type == "rds").first()
    if not server:
        server = db.query(ServerConfig).filter(ServerConfig.is_primary == True).first()
        if not server:
            raise HTTPException(status_code=400, detail="No hay ningún servidor configurado.")
            
    config = db.query(RdsConfig).filter(RdsConfig.server_id == server.id).first()
    
    # Use query params if provided, otherwise fallback to DB config
    final_temp_path = temp_path if temp_path else (config.temp_path if config else "C:\\conteo")
    final_file_prefix = file_prefix if file_prefix else (getattr(config, "file_prefix", "Nova_est") if config else "Nova_est")
    
    try:
        sessions = get_rds_sessions(server, final_temp_path, final_file_prefix)
        return {"success": True, "data": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/kill-and-clean")
async def kill_and_clean(req: KillRequest, db: Session = Depends(get_db)):
    server = db.query(ServerConfig).filter(ServerConfig.server_type == "rds").first()
    if not server:
        server = db.query(ServerConfig).filter(ServerConfig.is_primary == True).first()
        
    try:
        kill_rds_session(server, req.temp_path, req.session_id, req.username, req.file_prefix)
        return {"success": True, "message": "Sesión cerrada y temporales limpios."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schedule")
async def get_schedule(db: Session = Depends(get_db)):
    server = db.query(ServerConfig).filter(ServerConfig.server_type == "rds").first()
    if not server:
        server = db.query(ServerConfig).filter(ServerConfig.is_primary == True).first()
        
    config = db.query(RdsConfig).filter(RdsConfig.server_id == server.id).first() if server else None
    if config:
        task_status = query_remote_task(server) if server and config.is_active else None
        return {
            "success": True,
            "data": {
                "cron_time": config.cron_time,
                "cron_days": config.cron_days,
                "temp_path": config.temp_path,
                "file_prefix": getattr(config, "file_prefix", "Nova_est"),
                "is_active": config.is_active,
                "last_run": task_status["last_run"] if task_status else "No disponible",
                "next_run": task_status["next_run"] if task_status else "No disponible"
            }
        }
    return {"success": True, "data": None}

@router.post("/schedule")
async def save_schedule(req: ScheduleRequest, request: Request, db: Session = Depends(get_db)):
    server = db.query(ServerConfig).filter(ServerConfig.server_type == "rds").first()
    if not server:
        server = db.query(ServerConfig).filter(ServerConfig.is_primary == True).first()
        if not server:
            raise HTTPException(status_code=400, detail="No server configured.")
            
    config = db.query(RdsConfig).filter(RdsConfig.server_id == server.id).first()
    if not config:
        config = RdsConfig(server_id=server.id)
        db.add(config)
        
    config.cron_time = req.cron_time
    config.cron_days = req.cron_days
    config.temp_path = req.temp_path
    config.file_prefix = req.file_prefix
    config.is_active = True
    db.commit()
    
    # Programar nativamente en el servidor remoto
    if req.cron_time and req.cron_days:
        try:
            deploy_remote_task(server, req.temp_path, req.file_prefix, req.cron_time, req.cron_days)
        except Exception as e:
            # Revertir estado si falla
            config.is_active = False
            db.commit()
            raise HTTPException(status_code=500, detail=str(e))
        
    return {"success": True, "message": "Tarea programada nativamente en el servidor exitosa."}

@router.post("/schedule/disable")
async def disable_schedule(request: Request, db: Session = Depends(get_db)):
    server = db.query(ServerConfig).filter(ServerConfig.server_type == "rds").first()
    if not server:
        server = db.query(ServerConfig).filter(ServerConfig.is_primary == True).first()
    
    config = db.query(RdsConfig).filter(RdsConfig.server_id == server.id).first()
    if config:
        config.is_active = False
        db.commit()
        
    try:
        delete_remote_task(server)
    except Exception as e:
        pass # If it doesn't exist, ignore
        
    return {"success": True, "message": "Tarea remota desactivada."}
