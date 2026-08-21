from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import logging
import os

from app.services.gpo_agent import GpoAgent
from app.services.ad_service import get_all_gpos
from app.services import gpo_chat_agent
from app.services.dc_exec import run_on_dc

router = APIRouter()
logger = logging.getLogger(__name__)
gpo_agent = None

class GpoTemplateRequest(BaseModel):
    template_type: str
    params: dict
    name: str
    target_ou: str
    is_active: bool = True

class GpoAiRequest(BaseModel):
    prompt: str

class GpoExecuteRequest(BaseModel):
    script: str

class GpoChatMessage(BaseModel):
    role: str
    content: str

class GpoChatRequest(BaseModel):
    messages: list[GpoChatMessage]

@router.post("/generate/template")
async def generate_template(req: GpoTemplateRequest):
    """Generates a PowerShell script for common GPO templates."""
    script = ""
    gpo_name = req.name.replace('"', '""')
    link_enabled = "Yes" if req.is_active else "No"
    
    if req.template_type == "wallpaper":
        path = req.params.get("path", "\\\\Server\\Share\\wallpaper.jpg").replace("'", "''")
        script = f"""# Crear y configurar la Politica de Fondo de Pantalla Corporativo
$gpoName = "{gpo_name}"
Import-Module GroupPolicy
if (-not (Get-GPO -Name $gpoName -ErrorAction SilentlyContinue)) {{
    New-GPO -Name $gpoName | Out-Null
}}
Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -ValueName "Wallpaper" -Type String -Value '{path}'
Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -ValueName "WallpaperStyle" -Type String -Value "2"
"""
    elif req.template_type == "network_drive":
        letter = req.params.get("letter", "Z:")
        path = req.params.get("path", "\\\\Server\\Share")
        script = f"""# Crear y configurar la Política de Unidad de Red Mapeada
$gpoName = "{gpo_name}"
New-GPO -Name $gpoName | Out-Null
# Configuración mediante Preferencias de GPO (Drive Maps)
$xml = @"
<?xml version="1.0" encoding="utf-8"?>
<Drive>
  <Properties action="U" thisDrive="SHOW" allDrives="NOCHANGE" userName="" path="{path}" label="" persistent="1" useLetter="1" letter="{letter.replace(':', '')}"/>
</Drive>
"@
Set-GPPrefRegistryValue -Name $gpoName -Context User -Action Update -Key "HKCU\\Network\\{letter.replace(':', '')}" -ValueName "RemotePath" -Type String -Value "{path}"
"""
    elif req.template_type == "screen_lock":
        minutes = req.params.get("minutes", "15")
        seconds = int(minutes) * 60
        script = f"""# Crear y configurar la Política de Bloqueo de Pantalla Automático
$gpoName = "{gpo_name}"
New-GPO -Name $gpoName | Out-Null
Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Policies\\Microsoft\\Windows\\Control Panel\\Desktop" -ValueName "ScreenSaveActive" -Type String -Value "1"
Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Policies\\Microsoft\\Windows\\Control Panel\\Desktop" -ValueName "ScreenSaverIsSecure" -Type String -Value "1"
Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Policies\\Microsoft\\Windows\\Control Panel\\Desktop" -ValueName "ScreenSaveTimeOut" -Type String -Value "{seconds}"
"""
    elif req.template_type == "printer":
        path = req.params.get("path", "\\\\PrintServer\\PrinterName")
        script = f"""# Crear y configurar la Política de Despliegue de Impresora Compartida
$gpoName = "{gpo_name}"
New-GPO -Name $gpoName | Out-Null
Add-Printer -ConnectionName "{path}"
"""
    else:
        raise HTTPException(status_code=400, detail="Plantilla desconocida")

    # Vincular GPO a la Unidad Organizativa destino
    if req.target_ou:
        script += f"\n# Vincular GPO a la OU\nNew-GPLink -Name $gpoName -Target \"{req.target_ou}\" -LinkEnabled {link_enabled} | Out-Null\n"

    return {"script": script}

@router.post("/generate/ai")
async def generate_ai(req: GpoAiRequest):
    """Generates a PowerShell script via LLM."""
    global gpo_agent
    try:
        if gpo_agent is None:
            gpo_agent = GpoAgent()
        script = await gpo_agent.generate_gpo_script(req.prompt)
        return {"script": script}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def gpo_chat(req: GpoChatRequest):
    """Asistente conversacional para diseñar GPOs (Gemini Flash, Groq de respaldo)."""
    if not req.messages:
        raise HTTPException(status_code=400, detail="No hay mensajes")
    try:
        existing = []
        try:
            existing = [g.get("name") for g in get_all_gpos() if g.get("name")]
        except Exception as list_err:
            logger.warning("No se pudieron listar GPOs para el contexto del chat: %s", list_err)
        result = await gpo_chat_agent.chat(
            [{"role": m.role, "content": m.content} for m in req.messages],
            existing_gpos=existing,
        )
        return result
    except Exception as e:
        logger.error("Error en chat GPO: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_gpos():
    """Fetches all GPOs from Active Directory."""
    try:
        gpos = get_all_gpos()
        return gpos
    except Exception as e:
        logger.error(f"Error fetching GPOs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview-image")
async def preview_image(path: str):
    """Fetches an image from a UNC path to bypass browser security restrictions."""
    if not path or not path.startswith("\\\\"):
        raise HTTPException(status_code=400, detail="Ruta de red UNC no válida.")
        
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Imagen no encontrada en la ruta especificada.")
        
    try:
        # Check if file has a valid image extension to prevent arbitrary file reading
        valid_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        _, ext = os.path.splitext(path.lower())
        
        if ext not in valid_exts:
            raise HTTPException(status_code=400, detail="El archivo no es una imagen soportada.")
            
        return FileResponse(path)
    except Exception as e:
        logger.error(f"Error sirviendo previsualización de imagen {path}: {e}")
        raise HTTPException(status_code=500, detail="Error leyendo el archivo en el servidor.")


@router.post("/execute")
async def execute_script(req: GpoExecuteRequest):
    """Ejecuta el script de GPO en el Domain Controller via WMI (no WinRM)."""
    if not req.script.strip():
        raise HTTPException(status_code=400, detail="El script está vacío")

    try:
        logger.info("Ejecutando script de GPO en el DC via WMI")
        stdout = run_on_dc(req.script)
        return {
            "success": True,
            "stdout": stdout,
            "stderr": ""
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="El script tardó demasiado en ejecutarse (Timeout).")
    except Exception as e:
        logger.error(f"Error ejecutando GPO script: {e}")
        with open("gpo_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\nEXCEPTION:\n{str(e)}\n")
        raise HTTPException(status_code=500, detail=str(e))
