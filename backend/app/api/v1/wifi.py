from fastapi import APIRouter, HTTPException, Query
from app.services.unifi_service import unifi_service
from typing import Optional

router = APIRouter()

@router.get("/sites")
async def get_sites():
    try:
        sites = await unifi_service.get_sites()
        return {"success": True, "data": sites}
    except Exception as e:
        # Extraemos el mensaje de la excepción para retornarlo limpiamente
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/aps")
async def get_aps(site: str = Query("q0zet7qu", description="Nombre interno del sitio")):
    try:
        devices = await unifi_service.get_devices(site)
        result = []
        for d in devices:
            # UAP = UniFi Access Point
            if d.get("type") == "uap" or "mac" in d:
                result.append({
                    "mac": d.get("mac"),
                    "name": d.get("name") or d.get("mac"),
                    "ip": d.get("ip"),
                    "status": "online" if d.get("state") == 1 else "offline",
                    "model": d.get("model"),
                    "satisfaction": d.get("satisfaction", 0),
                    "clients_count": d.get("num_sta", 0)
                })
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/aps/{mac}/restart")
async def restart_ap(mac: str, site: str = Query("q0zet7qu")):
    try:
        res = await unifi_service.restart_ap(mac, site)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/aps/{mac}/history")
async def get_ap_history(mac: str, site: str = Query("q0zet7qu")):
    try:
        users = await unifi_service.get_all_clients(site)
        result = []
        for u in users:
            # En la lista de usuarios históricos, UniFi suele guardar ap_mac o last_ap_mac o last_uplink_mac
            ap_mac = u.get("ap_mac") or u.get("last_ap_mac") or u.get("last_uplink_mac")
            if ap_mac == mac:
                result.append({
                    "mac": u.get("mac"),
                    "hostname": u.get("hostname") or u.get("name") or u.get("mac"),
                    "ip": u.get("last_ip") or u.get("ip"),
                    "is_blocked": u.get("blocked", False),
                    "ap_mac": ap_mac,
                    "last_seen": u.get("last_seen")
                })
        
        # Ordenar por fecha de última conexión descendente si existe
        result.sort(key=lambda x: x.get("last_seen", 0) or 0, reverse=True)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clients")
async def get_clients(
    site: str = Query("q0zet7qu"),
    ap_mac: Optional[str] = None, 
    is_blocked: Optional[bool] = None
):
    try:
        # 1. Obtenemos los activos actuales
        active_users = await unifi_service.get_clients(site)
        
        # 2. Obtenemos el histórico para sacar los bloqueados (que ya no están activos)
        all_users = await unifi_service.get_all_clients(site)
        
        # Combinar evitando duplicados usando la MAC
        users_dict = {u.get("mac"): u for u in active_users}
        for u in all_users:
            if u.get("blocked") == True:
                users_dict[u.get("mac")] = u
                
        users = list(users_dict.values())
        
        result = []
        for u in users:
            if ap_mac and u.get("ap_mac") != ap_mac:
                continue
            
            blocked = u.get("blocked", False)
            if is_blocked is not None and blocked != is_blocked:
                continue
                
            # Manejar las diferentes formas en las que UniFi guarda la MAC del AP
            ap_mac_val = u.get("ap_mac") or u.get("last_ap_mac") or u.get("last_uplink_mac")

            result.append({
                "mac": u.get("mac"),
                "hostname": u.get("hostname") or u.get("name") or u.get("mac"),
                "ip": u.get("last_ip") or u.get("ip"),
                "is_blocked": blocked,
                "ap_mac": ap_mac_val,
                "last_seen": u.get("last_seen")
            })
        
        # Ordenar primero por activos (is_blocked=False) y luego alfabéticamente
        result.sort(key=lambda x: (x.get("is_blocked", False), str(x.get("hostname")).lower()))
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clients/{mac}/block")
async def block_client(mac: str, site: str = Query("q0zet7qu")):
    try:
        res = await unifi_service.block_client(mac, site)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clients/{mac}/unblock")
async def unblock_client(mac: str, site: str = Query("q0zet7qu")):
    try:
        res = await unifi_service.unblock_client(mac, site)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
