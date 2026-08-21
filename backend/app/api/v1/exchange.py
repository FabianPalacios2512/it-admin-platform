from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.exchange_service import grant_mailbox_permission, revoke_mailbox_permission, execute_powershell, log_audit
from app.services.graph_service import graph_service
import json

class AssignDelegateRequest(BaseModel):
    delegate: str
    permission: str

router = APIRouter()

@router.get("/{username}/delegates")
async def get_delegates(username: str, db: Session = Depends(get_db)):
    """Devuelve los delegados actuales del buzón."""
    # Resolver UPN del buzón
    user_id = await graph_service.resolve_user_id(username)
    if not user_id:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Obtener UPN
    endpoint = f"/users/{user_id}?$select=userPrincipalName"
    data = await graph_service._request("GET", endpoint)
    target_upn = data.get("userPrincipalName")
    
    if not target_upn:
        return {"success": True, "data": []}

    cmd = f'''
    $results = @()
    
    # Obtener FullAccess
    $mailboxPerms = Get-MailboxPermission -Identity "{target_upn}" -ErrorAction SilentlyContinue | Where-Object {{($_.User -notlike "NT AUTHORITY\*") -and ($_.IsInherited -eq $false) -and ($_.User -notlike "S-1-5-21*") -and ($_.User -ne "{target_upn}")}}
    foreach ($p in $mailboxPerms) {{
        $results += [PSCustomObject]@{{
            user = $p.User
            permission = "FullAccess"
        }}
    }}
    
    # Obtener SendAs
    $recipientPerms = Get-RecipientPermission -Identity "{target_upn}" -ErrorAction SilentlyContinue | Where-Object {{($_.Trustee -notlike "NT AUTHORITY\*") -and ($_.IsInherited -eq $false) -and ($_.Trustee -notlike "S-1-5-21*") -and ($_.Trustee -ne "{target_upn}")}}
    foreach ($p in $recipientPerms) {{
        $results += [PSCustomObject]@{{
            user = $p.Trustee
            permission = "SendAs"
        }}
    }}
    
    $results | ConvertTo-Json
    '''
    result = await execute_powershell(f"import-module ExchangeOnlineManagement; {cmd}")
    
    try:
        clean_result = result.replace('{"success": true}', '').strip()
        start_idx = -1
        for i, char in enumerate(clean_result):
            if char in ['{', '[']:
                start_idx = i
                break
        
        parsed_data = []
        if start_idx != -1:
            json_str = clean_result[start_idx:]
            data = json.loads(json_str)
            if isinstance(data, list):
                parsed_data = data
            elif isinstance(data, dict) and "error" not in data:
                parsed_data = [data]
        
        return {"success": True, "data": parsed_data}
    except Exception as e:
        print(f"Error parsing json in get_delegates: {e}")
        return {"success": True, "data": []}

@router.post("/{username}/delegates")
async def assign_delegate(username: str, req: AssignDelegateRequest, db: Session = Depends(get_db)):
    """Asigna un delegado al buzón."""
    # Target (The mailbox being modified)
    user_id = await graph_service.resolve_user_id(username)
    if not user_id:
        raise HTTPException(status_code=404, detail="Buzón no encontrado")
        
    data = await graph_service._request("GET", f"/users/{user_id}?$select=userPrincipalName")
    target_upn = data.get("userPrincipalName")
    
    if not target_upn:
        raise HTTPException(status_code=400, detail="El usuario no tiene un UPN válido.")
        
    source_upn = target_upn # mailbox
    delegate_upn = req.delegate # who gets access
    
    if req.permission not in ["FullAccess", "SendAs"]:
        raise HTTPException(status_code=400, detail="Permiso no soportado")
        
    success = await grant_mailbox_permission(source_upn, delegate_upn, req.permission)
    if not success:
        raise HTTPException(status_code=500, detail="Error al asignar el permiso en Exchange")
        
    log_audit("API", f"Asignar {req.permission}", f"{delegate_upn} -> {source_upn}", "Éxito")
    return {"success": True}

@router.delete("/{username}/delegates")
async def remove_delegate(username: str, req: AssignDelegateRequest, db: Session = Depends(get_db)):
    """Remueve un delegado del buzón."""
    user_id = await graph_service.resolve_user_id(username)
    if not user_id:
        raise HTTPException(status_code=404, detail="Buzón no encontrado")
        
    data = await graph_service._request("GET", f"/users/{user_id}?$select=userPrincipalName")
    target_upn = data.get("userPrincipalName")
    
    source_upn = target_upn
    delegate_upn = req.delegate
    
    success = await revoke_mailbox_permission(source_upn, delegate_upn, req.permission)
    if not success:
        raise HTTPException(status_code=500, detail="Error al remover el permiso en Exchange")
        
    log_audit("API", f"Remover {req.permission}", f"{delegate_upn} -> {source_upn}", "Éxito")
    return {"success": True}

