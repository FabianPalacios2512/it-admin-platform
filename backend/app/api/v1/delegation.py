from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.models.delegation import TemporaryDelegation
from app.services.exchange_service import sanitize_mailbox, grant_mailbox_permission, log_audit
from app.api.v1.auth import get_current_user
from app.services.graph_service import graph_service

router = APIRouter()

class TargetUser(BaseModel):
    upn: str
    permission: str # FullAccess, SendAs
    expiration: Optional[str] = None # ISO format date

class DelegationRequest(BaseModel):
    source_upn: str
    convert_shared: bool
    remove_license: bool
    hide_gal: bool
    retention_action: str # "none", "transfer", "link"
    retention_target: Optional[str] = None
    targets: List[TargetUser]

@router.get("/shared-mailboxes")
async def get_shared_mailboxes_list(current_user: dict = Depends(get_current_user)):
    from app.services.exchange_service import get_shared_mailboxes
    try:
        data = await get_shared_mailboxes()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/onedrive-link/{upn}")
async def get_onedrive_link(upn: str, current_user: dict = Depends(get_current_user)):
    try:
        user_id = await graph_service.resolve_user_id(upn)
        drive_info = await graph_service._request("GET", f"/users/{user_id}/drive?$select=webUrl")
        web_url = drive_info.get("webUrl")
        if not web_url:
            raise HTTPException(status_code=404, detail="OneDrive no encontrado o sin licencia")
        return {"url": web_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute")
async def execute_delegation_pipeline(
    request: DelegationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Ejecuta el Hub de Retención y Delegación (Sanitización, OneDrive, Exchange).
    """
    request.source_upn = request.source_upn.strip()
    
    admin_name = current_user.get("displayName", "Admin")
    admin_upn = current_user.get("userPrincipalName", "admin@domain")

    # 1. Sanitization (Exchange)
    if request.convert_shared or request.hide_gal:
        try:
            await sanitize_mailbox(request.source_upn, request.convert_shared, request.hide_gal)
            log_audit(admin_name, "Sanitización Exchange", request.source_upn, "Éxito", "DelegationHub")
        except Exception as e:
            log_audit(admin_name, "Sanitización Exchange", request.source_upn, f"Error: {str(e)}", "DelegationHub")
            # Continuar para permitir OneDrive incluso si la sanitización falla parcialmente

    # 2. Retención de Archivos (OneDrive) vía Graph API ANTES de quitar licencia
    master_link = None
    if request.retention_action == "transfer" and request.retention_target:
        try:
            await graph_service.transfer_onedrive(request.source_upn, request.retention_target)
            log_audit(admin_name, "Transferencia OneDrive", f"{request.source_upn} -> {request.retention_target}", "Éxito", "DelegationHub")
        except Exception as e:
            log_audit(admin_name, "Transferencia OneDrive", request.source_upn, f"Error: {str(e)}", "DelegationHub")
            
    elif request.retention_action == "link":
        try:
            res = await graph_service.generate_onedrive_master_link(request.source_upn)
            master_link = res.get("link")
            log_audit(admin_name, "Link Maestro OneDrive", request.source_upn, "Éxito", "DelegationHub")
        except Exception as e:
            log_audit(admin_name, "Link Maestro OneDrive", request.source_upn, f"Error: {str(e)}", "DelegationHub")

    # 3. Delegar accesos y registrar en BD si son temporales
    for target in request.targets:
        success = await grant_mailbox_permission(request.source_upn, target.upn, target.permission)
        if success:
            log_audit(admin_name, f"Delegación {target.permission}", f"{target.upn} -> {request.source_upn}", "Éxito", "DelegationHub")
            
            # Registrar acceso temporal si aplica
            if target.expiration:
                try:
                    exp_date = datetime.fromisoformat(target.expiration.replace("Z", "+00:00"))
                    temp_del = TemporaryDelegation(
                        source_upn=request.source_upn,
                        target_upn=target.upn,
                        permission_type=target.permission,
                        expiration_date=exp_date
                    )
                    db.add(temp_del)
                    db.commit()
                except Exception as e:
                    print(f"Error guardando en BD temporal: {e}")
        else:
            log_audit(admin_name, f"Fallo Delegación {target.permission}", f"{target.upn} -> {request.source_upn}", "Error", "DelegationHub")

    # 4. Remover Licencias (Graph API) - AL FINAL
    if request.remove_license:
        try:
            # Obtener perfil para ID
            user_id = await graph_service.resolve_user_id(request.source_upn)
            # Fetch assigned licenses
            data = await graph_service._request("GET", f"/users/{user_id}?$select=assignedLicenses")
            licenses = data.get("assignedLicenses", [])
            remove_skus = [lic["skuId"] for lic in licenses]
            if remove_skus:
                payload = {"addLicenses": [], "removeLicenses": remove_skus}
                await graph_service._request("POST", f"/users/{user_id}/assignLicense", json=payload)
            log_audit(admin_name, "Remover Licencias M365", request.source_upn, "Éxito", "DelegationHub")
        except Exception as e:
            log_audit(admin_name, "Remover Licencias M365", request.source_upn, f"Error: {str(e)}", "DelegationHub")

    response_data = {"success": True, "message": "Proceso de Offboarding/Delegación ejecutado exitosamente y auditado."}
    if master_link:
        response_data["master_link"] = master_link
        response_data["message"] += f" Link Maestro generado: {master_link}"
        
    return response_data
