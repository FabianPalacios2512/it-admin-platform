from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any, Optional
import jwt

from app.services.fortigate_service import FortigateService
from app.core.database import get_db
from app.models.audit import AuditLog
from app.api.v1.auth import SECRET_KEY, ALGORITHM
from sqlalchemy.orm import Session

router = APIRouter()
optional_oauth = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


def get_actor(token: Optional[str] = Depends(optional_oauth)) -> str:
    """Quién pulsó el botón. Sin automático: si no hay sesión, queda como operador."""
    if not token:
        return "operador"
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub") or "operador"
    except Exception:
        return "operador"


def log_noc_action(db: Session, username: str, action: str, target: str, status: str = "Éxito"):
    try:
        db.add(AuditLog(
            username=username,
            action=action,
            target=target,
            status=status,
            source="FortiGate-NOC",
        ))
        db.commit()
    except Exception as exc:
        print(f"No se pudo guardar bitácora NOC: {exc}")
        db.rollback()

import os
from pathlib import Path
from dotenv import load_dotenv

# Ruta del .env
env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'

def get_fortigate_token(ip: str) -> str:
    """
    Obtiene el token del FortiGate desde las variables de entorno.
    Formato esperado en .env: FORTIGATE_TOKEN_192_168_40_16="tu_token"
    """
    # Forzar recarga del archivo .env en cada petición para no tener que reiniciar el backend
    load_dotenv(dotenv_path=env_path, override=True)
    env_var_name = f"FORTIGATE_TOKEN_{ip.replace('.', '_')}"
    return os.getenv(env_var_name)

@router.get("/{ip}/diagnostics")
def get_fortigate_diagnostics(ip: str):
    token = get_fortigate_token(ip)
    if not token:
        # Si no tenemos token para este equipo, devolvemos error
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
        
    service = FortigateService(ip, token)
    diagnostics = service.get_diagnostics()
    
    return diagnostics


@router.get("/{ip}/hosts")
def get_fortigate_hosts(ip: str):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    service = FortigateService(ip, token)
    hosts = service.list_hosts()
    return {"hosts": hosts, "count": len(hosts)}


@router.get("/{ip}/traffic/audit")
def get_fortigate_traffic_audit(
    ip: str,
    realtime: bool = Query(True),
    start: Optional[int] = Query(None),
    end: Optional[int] = Query(None),
    srcip: Optional[str] = Query(None),
):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    service = FortigateService(ip, token)
    return service.get_traffic_audit(realtime=realtime, start=start, end=end, srcip=srcip)


@router.get("/{ip}/traffic/session-detail")
def get_fortigate_session_detail(
    ip: str,
    srcip: str = Query(...),
    dstip: Optional[str] = Query(None),
    dst_host: Optional[str] = Query(None),
):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    service = FortigateService(ip, token)
    return service.get_session_detail(srcip, dstip=dstip, dst_host=dst_host)


@router.get("/{ip}/traffic/sessions")
def get_fortigate_sessions(ip: str, count: int = Query(200, ge=1, le=1000)):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    service = FortigateService(ip, token)
    sessions = [service._normalize_session(s) for s in service.get_sessions(count)]
    return {"session_count": len(sessions), "sessions": sessions}

from pydantic import BaseModel


class BanRequest(BaseModel):
    ip: str = ""
    mac: str = ""
    expiry: int = 3600  # segundos; 0 = indefinido
    reason: str = ""


@router.get("/{ip}/security/banned")
def get_banned_ips(ip: str):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    service = FortigateService(ip, token)
    return {"banned": service.list_banned(), "mac_blocks": service.list_mac_blocks()}


@router.post("/{ip}/security/ban")
def ban_ip(ip: str, request: BanRequest, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        target = service.resolve_isolate_target(request.ip, request.mac)
        result = service.ban_ip(target["ip"], request.expiry)
        label = target["ip"]
        if target.get("mac"):
            label = f"{target['ip']} MAC {target['mac']}"
        note = request.reason.strip() if request.reason else ""
        log_noc_action(db, actor, "Cuarentena host", f"{label} @ {ip}" + (f" · {note}" if note else ""))
        return {
            "status": "success",
            "message": f"{target['ip']} aislado de la red.",
            "ip": target["ip"],
            "mac": target.get("mac") or "",
            "hostname": target.get("hostname") or "",
            "data": result,
        }
    except Exception as e:
        log_noc_action(db, actor, "Cuarentena host", f"{request.ip} @ {ip}", f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ip}/security/ban/{target_ip}")
def unban_ip(ip: str, target_ip: str, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        result = service.unban_ip(target_ip)
        log_noc_action(db, actor, "Habilitar host", f"{target_ip} @ {ip}")
        return {"status": "success", "message": f"{target_ip} habilitada de nuevo. Ya puede salir a la red.", "data": result}
    except Exception as e:
        log_noc_action(db, actor, "Habilitar host", f"{target_ip} @ {ip}", f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BanMacRequest(BaseModel):
    mac: str
    ip: str = ""
    reason: str = ""


@router.post("/{ip}/security/ban-mac")
def ban_mac(ip: str, request: BanMacRequest, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        result = service.ban_mac(request.mac, request.reason, request.ip)
        log_noc_action(db, actor, "Bloqueo MAC", f"{result.get('mac')} {result.get('ip') or ''} @ {ip}" + (f" · {request.reason}" if request.reason else ""))
        return {"status": "success", "message": f"MAC {result.get('mac')} bloqueada.", **result}
    except Exception as e:
        log_noc_action(db, actor, "Bloqueo MAC", f"{request.mac} @ {ip}", f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ip}/security/ban-mac/{mac}")
def unban_mac(ip: str, mac: str, db: Session = Depends(get_db), actor: str = Depends(get_actor)):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        result = service.unban_mac(mac)
        log_noc_action(db, actor, "Liberar MAC", f"{mac} @ {ip}")
        return {"status": "success", "message": f"MAC {mac} liberada.", "data": result}
    except Exception as e:
        log_noc_action(db, actor, "Liberar MAC", f"{mac} @ {ip}", f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------
# God Mode: acciones tácticas del módulo de Administración (NOC/SOC)
# ----------------------------------------------------------------------

class KillSessionRequest(BaseModel):
    srcip: str
    dstip: str
    proto: str = "tcp"
    sport: int = 0
    dport: int = 0


@router.post("/{ip}/security/session/kill")
def kill_session(ip: str, request: KillSessionRequest):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        result = service.kill_session(request.srcip, request.dstip, request.proto, request.sport, request.dport)
        return {
            "status": "success",
            "message": f"Señal de cierre enviada para la sesión {request.srcip} → {request.dstip}.",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ip}/shaping/assignments")
def get_shaping_assignments(ip: str):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        return {"assignments": service.list_shaping_assignments()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ip}/shaping/profiles")
def get_shaper_profiles(ip: str):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        return {"profiles": service.list_shaper_profiles()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ShapeRequest(BaseModel):
    target_ip: str
    max_mbps: Optional[float] = None
    shaper_name: Optional[str] = None
    direction: Optional[str] = "symmetric"
    origin: Optional[str] = "manual"


class DestinationActionRequest(BaseModel):
    srcip: str
    dstip: Optional[str] = None
    dst_host: Optional[str] = None
    max_mbps: Optional[float] = None
    shaper_name: Optional[str] = None
    cascade: Optional[bool] = True
    srcintf: Optional[str] = None
    dstintf: Optional[str] = None


@router.get("/{ip}/security/destination/blocks")
def list_destination_blocks(ip: str):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    service = FortigateService(ip, token)
    return {"blocks": service.list_destination_blocks()}


@router.post("/{ip}/security/destination/block/preview")
def preview_destination_block(ip: str, request: DestinationActionRequest):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        return service.preview_destination_block(request.srcip, request.dstip or "", request.dst_host or "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ip}/security/destination/block")
def block_destination(
    ip: str,
    request: DestinationActionRequest,
    db: Session = Depends(get_db),
    actor: str = Depends(get_actor),
):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        cascade = True if request.cascade is None else bool(request.cascade)
        result = service.block_destination(request.srcip, request.dstip or "", request.dst_host or "", cascade=cascade)
        label = result.get("dest")
        message = f"{label} bloqueado."
        if result.get("warning"):
            message += f" ⚠ {result['warning']}"
        log_noc_action(db, actor, f"Bloquear destino {label}", f"{request.srcip} → {result.get('domains_label') or label} @ {ip}")
        return {
            "status": "success",
            "message": message,
            "data": result,
        }
    except Exception as e:
        log_noc_action(db, actor, "Bloquear destino", f"{request.srcip} @ {ip}", f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ip}/security/destination/block")
def unblock_destination(
    ip: str,
    srcip: str = Query(...),
    dest_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    actor: str = Depends(get_actor),
):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        result = service.unblock_destination(srcip, dest_name or "")
        log_noc_action(
            db,
            actor,
            f"Revertir bloqueo {dest_name or 'todos'}",
            f"{srcip} → {dest_name or 'todos los destinos'} @ {ip}",
        )
        return {
            "status": "success",
            "message": f"Revertido: {srcip} vuelve a poder hablar con {dest_name or 'los destinos que tenía bloqueados'}.",
            "data": result,
        }
    except Exception as e:
        log_noc_action(db, actor, "Revertir bloqueo", f"{srcip} @ {ip}", f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ip}/shaping/destination")
def shape_destination(ip: str, request: DestinationActionRequest):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    if not request.max_mbps and not request.shaper_name:
        raise HTTPException(status_code=400, detail="Indica cuántos Mbps quieres limitar.")
    try:
        service = FortigateService(ip, token)
        result = service.apply_destination_shaper(
            request.srcip,
            request.shaper_name or "",
            request.dstip or "",
            request.dst_host or "",
            srcintf=request.srcintf or "",
            dstintf=request.dstintf or "",
            max_mbps=request.max_mbps,
        )
        detail = result.get("dest") or result.get("domains_label")
        mbps = result.get("mbps") or 1
        message = f"{detail} limitado a {mbps:g} Mbps en este equipo. Corta la descarga y vuelve a abrirla para que el tope entre."
        if result.get("warning"):
            message += f" ⚠ {result['warning']}"
        return {
            "status": "success",
            "message": message,
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ip}/shaping/apply")
def apply_shaper(ip: str, request: ShapeRequest):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    if not request.max_mbps and not request.shaper_name:
        raise HTTPException(status_code=400, detail="Indica cuántos Mbps quieres limitar.")
    try:
        service = FortigateService(ip, token)
        profile = service._profile_for_limit(request.shaper_name or "", request.max_mbps)
        direction = (request.direction or "symmetric").lower()
        if direction not in ("rx", "symmetric"):
            direction = "symmetric"
        origin = (request.origin or "manual").lower()
        if origin not in ("preset", "manual"):
            origin = "manual"
        result = service.apply_traffic_shaper(
            request.target_ip, profile["name"], request.max_mbps, direction=direction, origin=origin
        )
        dir_label = "descarga" if direction == "rx" else "simétrico"
        return {
            "status": "success",
            "message": f"{request.target_ip} limitado a {profile['label']} ({dir_label}).",
            "data": result,
            "mbps": round(profile["max_bandwidth_kbps"] / 1000, 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ip}/shaping/apply/{target_ip}")
def remove_shaper(ip: str, target_ip: str, policy_name: Optional[str] = Query(None)):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        result = service.remove_traffic_shaper(target_ip or "", policy_name or "")
        return {"status": "success", "message": "Límite quitado.", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ip}/shaping/assignment")
def remove_shaping_assignment(ip: str, policy_name: str = Query(...)):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        result = service.remove_traffic_shaper(policy_name=policy_name)
        return {"status": "success", "message": "Límite quitado.", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BlockAppRequest(BaseModel):
    app_name: str
    profile_name: str = "default"


@router.post("/{ip}/security/block-application")
def block_application(ip: str, request: BlockAppRequest):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    try:
        service = FortigateService(ip, token)
        result = service.block_application(request.app_name, request.profile_name)
        return {
            "status": "success",
            "message": f"'{request.app_name}' añadida a la lista negra del perfil '{request.profile_name}'.",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DHCPReservationRequest(BaseModel):
    mac: str
    ip: str
    createFirewallAddress: bool = False

@router.post("/{ip}/dhcp/reservation")
def reserve_dhcp_lease(ip: str, request: DHCPReservationRequest):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    
    try:
        service = FortigateService(ip, token)
        result = service.reserve_dhcp(request.mac, request.ip, request.createFirewallAddress)
        return {"status": "success", "message": f"Reservación creada para {request.mac} con IP {request.ip}", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RevokeRequest(BaseModel):
    mac: str
    server_mkey: int = None  # ID del servidor DHCP del FortiGate (de server_mkey del lease)

@router.delete("/{ip}/dhcp/reservation")
def revoke_dhcp_reservation(ip: str, request: RevokeRequest):
    token = get_fortigate_token(ip)
    if not token:
        raise HTTPException(status_code=403, detail="API Token no configurado para este FortiGate.")
    
    try:
        service = FortigateService(ip, token)
        result = service.revoke_dhcp(request.mac, server_id=request.server_mkey)
        return {"status": "success", "message": f"Reservación revocada para {request.mac}", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
