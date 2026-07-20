from fastapi import APIRouter, HTTPException, Query
from app.services.unifi_service import unifi_service
from typing import Optional

router = APIRouter()

@router.get("/aps")
async def get_aps():
    try:
        devices = await unifi_service.get_devices()
        result = []
        for d in devices:
            # UAP = UniFi Access Point
            if d.get("type") == "uap" or "mac" in d:
                result.append({
                    "mac": d.get("mac"),
                    "name": d.get("name") or d.get("mac"),
                    "ip": d.get("ip"),
                    "status": "online" if d.get("state") == 1 else "offline",
                    "model": d.get("model")
                })
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/aps/{mac}/restart")
async def restart_ap(mac: str):
    try:
        res = await unifi_service.restart_ap(mac)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clients")
async def get_clients(ap_mac: Optional[str] = None, is_blocked: Optional[bool] = None):
    try:
        users = await unifi_service.get_all_users()
        result = []
        for u in users:
            if ap_mac and u.get("ap_mac") != ap_mac:
                continue
            
            blocked = u.get("blocked", False)
            if is_blocked is not None and blocked != is_blocked:
                continue
                
            result.append({
                "mac": u.get("mac"),
                "hostname": u.get("hostname") or u.get("name") or u.get("mac"),
                "ip": u.get("last_ip") or u.get("ip"),
                "is_blocked": blocked,
                "ap_mac": u.get("ap_mac"),
                "last_seen": u.get("last_seen")
            })
        
        result.sort(key=lambda x: str(x.get("hostname")).lower())
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clients/{mac}/block")
async def block_client(mac: str):
    try:
        res = await unifi_service.block_client(mac)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clients/{mac}/unblock")
async def unblock_client(mac: str):
    try:
        res = await unifi_service.unblock_client(mac)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
