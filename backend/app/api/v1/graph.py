from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.graph_service import graph_service
from app.core.database import get_db
from app.models.server import ServerConfig
from app.core.encryption import decrypt_password
import subprocess

class AssignLicenseRequest(BaseModel):
    username: str
    sku_id: str

class MfaStatusRequest(BaseModel):
    enable: bool

router = APIRouter()

@router.get("/licenses", response_model=List[Dict[str, Any]])
async def get_licenses():
    """Devuelve el estado de las licencias (compradas vs asignadas) desde Entra ID."""
    try:
        return await graph_service.get_subscribed_skus()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/licenses/summary")
async def get_licenses_summary():
    """Devuelve un mapa de {username: bool} indicando si tienen licencia asignada."""
    try:
        summary = await graph_service.get_all_users_license_summary()
        return {"success": True, "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-ad")
async def force_ad_sync(db: Session = Depends(get_db)):
    """Fuerza un ciclo delta de sincronización de Entra Connect de forma remota."""
    try:
        # Obtener el servidor primario (AD)
        server = db.query(ServerConfig).filter(ServerConfig.server_type == "da", ServerConfig.is_primary == True).first()
        if not server:
            return {"success": False, "detail": "No hay un servidor AD primario configurado."}
        
        try:
            admin_pass = decrypt_password(server.admin_pass)
        except Exception as e:
            return {"success": False, "detail": "Error desencriptando la contraseña del servidor."}

        # Ejecutar remotamente vía WMI (Bypasses WinRM/TrustedHosts)
        ps_script = f'''
$password = ConvertTo-SecureString "{admin_pass}" -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential ("{server.admin_user}", $password)
Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList 'powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-ADSyncSyncCycle -PolicyType Delta"' -ComputerName "{server.ip}" -Credential $credential
'''
        result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
        if result.returncode == 0:
            return {"success": True, "message": "Sincronización iniciada remotamente en el servidor.", "stdout": result.stdout}
        else:
            return {"success": False, "detail": f"Error PowerShell Remoto: {result.stderr or result.stdout}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{username}/revoke-sessions")
async def revoke_user_sessions(username: str):
    """Revoca todas las sesiones activas en Entra ID para un usuario."""
    try:
        await graph_service.revoke_sessions(username)
        return {"success": True, "message": f"Sesiones revocadas para {username}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/licenses/{username}")
async def get_user_licenses(username: str):
    """Devuelve las licencias asignadas actualmente a un usuario en Entra ID."""
    try:
        licenses = await graph_service.get_user_licenses(username)
        return {"success": True, "data": licenses}
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                err_data = e.response.json()
                error_msg = err_data.get('error', {}).get('message', str(e))
            except:
                pass
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/licenses/assign")
async def assign_license(req: AssignLicenseRequest):
    """Asigna una licencia a un usuario en Entra ID."""
    try:
        result = await graph_service.assign_license(req.username, req.sku_id)
        return {"success": True, "message": "Licencia asignada correctamente", "data": result}
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                err_data = e.response.json()
                error_msg = err_data.get('error', {}).get('message', str(e))
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error al asignar licencia: {error_msg}")

@router.get("/sync-status")
async def get_sync_status():
    """Devuelve la fecha de la última sincronización de Entra Connect."""
    try:
        last_sync = await graph_service.get_sync_status()
        return {"onPremisesLastSyncDateTime": last_sync}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/security-radar", response_model=List[Dict[str, Any]])
async def get_security_radar():
    """Devuelve los últimos inicios de sesión fallidos desde Entra ID."""
    try:
        return await graph_service.get_security_alerts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/security/risky-users")
async def get_risky_users():
    try:
        return await graph_service.get_risky_users()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/security/risk-detections")
async def get_risk_detections():
    try:
        return await graph_service.get_risk_detections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{username}/revoke-sessions")
async def revoke_user_sessions(username: str):
    try:
        return await graph_service.revoke_user_sessions(username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{username}/devices")
async def get_user_devices(username: str):
    """Devuelve los dispositivos de un usuario (Hardware)."""
    try:
        devices = await graph_service.get_user_devices(username)
        return {"success": True, "data": devices}
    except ValueError as e:
        if "No se encontró" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{username}/mailbox")
async def get_user_mailbox(username: str):
    """Devuelve la info de buzón del usuario."""
    try:
        mailbox = await graph_service.get_mailbox_info(username)
        return {"success": True, "data": mailbox}
    except ValueError as e:
        if "No se encontró" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{username}/entra-status")
async def get_user_entra_status(username: str):
    """Devuelve el estado en Entra ID."""
    try:
        result = await graph_service.get_entra_user_status(username)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return {"success": True, "data": result["data"]}
    except HTTPException:
        raise
    except ValueError as e:
        if "No se encontró" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{username}/reset-mfa")
async def reset_user_mfa(username: str):
    """Borra todos los métodos MFA del usuario obligándolo a registrarse nuevamente."""
    try:
        result = await graph_service.reset_user_mfa(username)
        return result
    except ValueError as e:
        if "No se encontró" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{username}/offboard")
async def offboard_user(username: str):
    """Desvinculación express (Macro-acción) en Entra ID."""
    try:
        result = await graph_service.offboard_user(username)
        return result
    except ValueError as e:
        if "No se encontró" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{username}/mfa-status")
async def get_user_mfa_status(username: str):
    """Devuelve el estado MFA del usuario (enabled/disabled) mediante strongAuthenticationRequirements."""
    try:
        result = await graph_service.get_user_mfa_status(username)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except ValueError as e:
        if "No se encontró" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/{username}/mfa-status")
async def set_user_mfa_status(username: str, req: MfaStatusRequest):
    """Habilita o deshabilita el MFA del usuario mediante strongAuthenticationRequirements."""
    try:
        result = await graph_service.set_user_mfa_status(username, req.enable)
        return result
    except ValueError as e:
        if "No se encontró" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

