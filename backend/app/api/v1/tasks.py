from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from app.core.task_manager import get_user_tasks, get_task
from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/")
async def list_user_tasks(username: str, status: str = None, db: Session = Depends(get_db)):
    """Obtiene las tareas recientes (opcionalmente filtradas por estado) de un usuario."""
    # Para mayor seguridad en el futuro, username debería extraerse del token JWT.
    # Por ahora, usamos el parámetro query para compatibilidad con la arquitectura actual.
    if not username:
        raise HTTPException(status_code=400, detail="username es requerido")
        
    tasks = get_user_tasks(username, status)
    return {"success": True, "data": tasks}

@router.get("/{task_id}")
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Obtiene el estado de una tarea específica."""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return {"success": True, "data": task}
