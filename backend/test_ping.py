import sys
sys.path.append('.')
from fastapi import APIRouter
from app.services.printer_service import _execute_remote_ps
import subprocess

def ping_printer(ip: str):
    if ip.startswith("WSD-"):
        return {"success": False, "message": "No se puede hacer ping directo a un puerto WSD."}
    
    # Ping locally from backend
    res = subprocess.run(["ping", "-n", "2", "-w", "1000", ip], capture_output=True, text=True)
    if res.returncode == 0:
        return {"success": True, "message": "Responde al Ping"}
    else:
        return {"success": False, "message": "No responde (Offline)"}
