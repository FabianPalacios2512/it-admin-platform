from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
import dotenv
import hashlib

router = APIRouter()

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ".env")

class SetupMaster(BaseModel):
    master_password: str

class VerifyMaster(BaseModel):
    master_password: str

class ConfigUpdate(BaseModel):
    master_password: str
    ENTRA_TENANT_ID: str | None = None
    ENTRA_CLIENT_ID: str | None = None
    ENTRA_CLIENT_SECRET: str | None = None

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_env_dict():
    if not os.path.exists(ENV_PATH):
        return {}
    config = {}
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                val = val.strip().strip("'").strip('"')
                config[key.strip()] = val
    return config

@router.get("/status")
def get_status():
    config = get_env_dict()
    is_setup = "SETUP_MASTER_PASSWORD_HASH" in config
    return {"is_setup": is_setup}

@router.post("/setup")
def setup_master_password(payload: SetupMaster):
    config = get_env_dict()
    if "SETUP_MASTER_PASSWORD_HASH" in config:
        raise HTTPException(status_code=400, detail="La clave maestra ya está configurada.")
    
    hashed = hash_password(payload.master_password)
    
    with open(ENV_PATH, "a", encoding="utf-8") as f:
        f.write(f'\n# Master Password para seguridad de la UI\nSETUP_MASTER_PASSWORD_HASH="{hashed}"\n')
        
    dotenv.load_dotenv(ENV_PATH, override=True)
    return {"message": "Clave maestra configurada exitosamente."}

@router.post("/verify")
def verify_master_password(payload: VerifyMaster):
    config = get_env_dict()
    saved_hash = config.get("SETUP_MASTER_PASSWORD_HASH")
    if not saved_hash:
        raise HTTPException(status_code=400, detail="El sistema no está inicializado.")
        
    if hash_password(payload.master_password) != saved_hash:
        raise HTTPException(status_code=401, detail="Clave maestra incorrecta.")
        
    # Return only the allowed fields
    return {
        "ENTRA_TENANT_ID": config.get("ENTRA_TENANT_ID", ""),
        "ENTRA_CLIENT_ID": config.get("ENTRA_CLIENT_ID", ""),
        "ENTRA_CLIENT_SECRET": config.get("ENTRA_CLIENT_SECRET", "")
    }

@router.post("/config")
def update_config(updates: ConfigUpdate):
    config = get_env_dict()
    saved_hash = config.get("SETUP_MASTER_PASSWORD_HASH")
    if not saved_hash or hash_password(updates.master_password) != saved_hash:
        raise HTTPException(status_code=401, detail="No autorizado.")
    
    update_dict = {
        "ENTRA_TENANT_ID": updates.ENTRA_TENANT_ID,
        "ENTRA_CLIENT_ID": updates.ENTRA_CLIENT_ID,
        "ENTRA_CLIENT_SECRET": updates.ENTRA_CLIENT_SECRET
    }
    # Filter out None
    update_dict = {k: v for k, v in update_dict.items() if v is not None}
    
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    new_lines = []
    updated_keys = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
            
        if "=" in stripped:
            key, val = stripped.split("=", 1)
            key = key.strip()
            if key in update_dict:
                new_val = update_dict[key]
                if " " in new_val or "~" in new_val or "-" in new_val:
                     new_lines.append(f'{key}="{new_val}"\n')
                else:
                     new_lines.append(f'{key}={new_val}\n')
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    for key, val in update_dict.items():
        if key not in updated_keys:
            if " " in val or "~" in val or "-" in val:
                 new_lines.append(f'{key}="{val}"\n')
            else:
                 new_lines.append(f'{key}={val}\n')
            
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    dotenv.load_dotenv(ENV_PATH, override=True)
    
    return {"message": "Configuración actualizada exitosamente."}
