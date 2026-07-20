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
def get_recent_audit_logs(limit: int = 15, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    return logs
