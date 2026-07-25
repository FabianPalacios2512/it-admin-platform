from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.models.audit import AuditLog
from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    username: str
    action: str
    target: str
    status: str
    source: str

    class Config:
        from_attributes = True # updated for pydantic v2

@router.get("", response_model=List[AuditLogResponse])
def get_recent_audit_logs(
    limit: int = 100, 
    source: str = None, 
    action: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if source:
        query = query.filter(AuditLog.source == source)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
        
    logs = query.order_by(desc(AuditLog.timestamp)).limit(limit).all()
    return logs

@router.get("/ad-events")
def get_ad_security_events(limit: int = 50):
    """Obtiene los eventos críticos del Event Viewer del Controlador de Dominio (o servidor local)."""
    try:
        from app.services.ad_audit_service import get_critical_ad_events
        events = get_critical_ad_events(limit=limit)
        return {"success": True, "data": events}
    except Exception as e:
        return {"success": False, "error": str(e)}
