from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import subprocess
import logging

from app.services.gpo_agent import GpoAgent

router = APIRouter()
logger = logging.getLogger(__name__)
gpo_agent = GpoAgent()

class GpoTemplateRequest(BaseModel):
    template_type: str
    params: dict

class GpoAiRequest(BaseModel):
    prompt: str

class GpoExecuteRequest(BaseModel):
    script: str

@router.post("/generate/template")
async def generate_template(req: GpoTemplateRequest):
    """Generates a PowerShell script for common GPO templates."""
    script = ""
    if req.template_type == "wallpaper":
        path = req.params.get("path", "\\\\Server\\Share\\wallpaper.jpg")
        script = f"""# Crear y configurar la Política de Fondo de Pantalla Corporativo
$gpoName = "Fondo de Pantalla Corporativo"
New-GPO -Name $gpoName | Out-Null
Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -ValueName "Wallpaper" -Type String -Value "{path}"
Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -ValueName "WallpaperStyle" -Type String -Value "2"
"""
    elif req.template_type == "network_drive":
        letter = req.params.get("letter", "Z:")
        path = req.params.get("path", "\\\\Server\\Share")
        script = f"""# Crear y configurar la Política de Unidad de Red Mapeada
$gpoName = "Mapeo de Unidad de Red {letter}"
New-GPO -Name $gpoName | Out-Null
# Configuración mediante Preferencias de GPO (Drive Maps)
$xml = @"
<?xml version="1.0" encoding="utf-8"?>
<Drive>
  <Properties action="U" thisDrive="SHOW" allDrives="NOCHANGE" userName="" path="{path}" label="" persistent="1" useLetter="1" letter="{letter.replace(':', '')}"/>
</Drive>
"@
Set-GPPrefRegistryValue -Name $gpoName -Context User -Action Update -Key "HKCU\\Network\\{letter.replace(':', '')}" -ValueName "RemotePath" -Type String -Value "{path}"
# Nota: La creación perfecta de Drives Mapped por script suele requerir manipular el XML del SYSVOL, 
# pero usar Set-GPRegistryValue como arriba provee un mapeo básico en el registro.
"""
    elif req.template_type == "screen_lock":
        minutes = req.params.get("minutes", "15")
        seconds = int(minutes) * 60
        script = f"""# Crear y configurar la Política de Bloqueo de Pantalla Automático
$gpoName = "Bloqueo de Pantalla - {minutes} Minutos"
New-GPO -Name $gpoName | Out-Null
Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Policies\\Microsoft\\Windows\\Control Panel\\Desktop" -ValueName "ScreenSaveActive" -Type String -Value "1"
Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Policies\\Microsoft\\Windows\\Control Panel\\Desktop" -ValueName "ScreenSaverIsSecure" -Type String -Value "1"
Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Policies\\Microsoft\\Windows\\Control Panel\\Desktop" -ValueName "ScreenSaveTimeOut" -Type String -Value "{seconds}"
"""
    elif req.template_type == "printer":
        path = req.params.get("path", "\\\\PrintServer\\PrinterName")
        script = f"""# Crear y configurar la Política de Despliegue de Impresora Compartida
$gpoName = "Despliegue Impresora Compartida"
New-GPO -Name $gpoName | Out-Null
# Nota: Configurar el despliegue nativo de impresoras requiere el módulo PrintManagement.
Add-Printer -ConnectionName "{path}"
"""
    else:
        raise HTTPException(status_code=400, detail="Plantilla desconocida")

    return {"script": script}

@router.post("/generate/ai")
async def generate_ai(req: GpoAiRequest):
    """Generates a PowerShell script via LLM."""
    try:
        script = await gpo_agent.generate_gpo_script(req.prompt)
        return {"script": script}
    except Exception as e:
        logger.error(f"Error en generate_ai: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute")
async def execute_script(req: GpoExecuteRequest):
    """Executes the PowerShell script locally on the DC."""
    if not req.script.strip():
        raise HTTPException(status_code=400, detail="El script está vacío")
    
    try:
        # Importante: Como se nos pidió en las reglas, ejecutamos en modo local,
        # asumiendo que este backend se ejecuta en un servidor con las herramientas RSAT de AD.
        # En Producción real con servidores externos, esto se pasaría por WinRM (Invoke-Command).
        
        logger.info("Ejecutando script de GPO")
        
        # Ejecutar powershell localmente
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", req.script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=60)
        
        if process.returncode != 0:
            logger.error(f"Error ejecutando GPO: {stderr}")
            raise Exception(f"PowerShell devolvió código {process.returncode}:\n{stderr}")
            
        return {
            "success": True,
            "stdout": stdout,
            "stderr": stderr
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="El script tardó demasiado en ejecutarse (Timeout).")
    except Exception as e:
        logger.error(f"Error ejecutando GPO script: {e}")
        raise HTTPException(status_code=500, detail=str(e))
