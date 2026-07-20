from fastapi import APIRouter, HTTPException
from app.services.devices_service import get_all_devices, ping_device, reboot_device, get_bitlocker_status
from pydantic import BaseModel

router = APIRouter(tags=["Devices"])

class ActionRequest(BaseModel):
    hostname: str

@router.get("/")
async def list_devices():
    try:
        devices = get_all_devices()
        return {"success": True, "data": devices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ping")
async def action_ping(req: ActionRequest):
    try:
        is_online = ping_device(req.hostname)
        return {"success": True, "online": is_online}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reboot")
async def action_reboot(req: ActionRequest):
    try:
        reboot_device(req.hostname)
        return {"success": True, "message": f"Orden de reinicio enviada a {req.hostname}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bitlocker")
async def action_bitlocker(req: ActionRequest):
    try:
        status = get_bitlocker_status(req.hostname)
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
