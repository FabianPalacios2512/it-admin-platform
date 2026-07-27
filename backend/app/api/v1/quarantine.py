from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.audit import AuditLog
from app.services.graph_service import get_quarantined_emails_ps, release_quarantined_email_ps, check_exchange_setup, setup_exchange
from pydantic import BaseModel

router = APIRouter()

class ReleaseRequest(BaseModel):
    identity: str
    user_email: str
    username_requesting: str # Para auditoría

@router.get("/status")
async def get_quarantine_status():
    """Devuelve el estado de la configuración de Exchange Online."""
    try:
        status = await check_exchange_setup()
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/setup")
async def run_exchange_setup():
    """Ejecuta la configuración automática de Exchange Online."""
    try:
        result = await setup_exchange()
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from typing import Optional

@router.get("/search")
async def search_quarantine(
    email: Optional[str] = None, 
    sender: Optional[str] = None, 
    subject: Optional[str] = None, 
    qtype: Optional[str] = None
):
    """Busca correos en cuarentena con filtros opcionales."""
    try:
        results = await get_quarantined_emails_ps(
            recipient=email,
            sender=sender,
            subject=subject,
            quarantine_type=qtype
        )
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/release")
async def release_quarantine(req: ReleaseRequest, db: Session = Depends(get_db)):
    """Libera un correo de la cuarentena."""
    try:
        # Ejecutar liberación
        result = await release_quarantined_email_ps(req.identity)
        
        # Auditoría obligatoria
        audit = AuditLog(
            username=req.username_requesting,
            action="RELEASE_QUARANTINE_EMAIL",
            target=f"{req.user_email} (MsgID: {req.identity})",
            status="SUCCESS",
            source="Web - Quarantine Module"
        )
        db.add(audit)
        db.commit()
        
        return {"success": True, "message": "Correo liberado exitosamente"}
    except Exception as e:
        # Log failure
        audit_err = AuditLog(
            username=req.username_requesting,
            action="RELEASE_QUARANTINE_EMAIL",
            target=f"{req.user_email} (MsgID: {req.identity})",
            status="FAILED",
            source="Web - Quarantine Module"
        )
        db.add(audit_err)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
