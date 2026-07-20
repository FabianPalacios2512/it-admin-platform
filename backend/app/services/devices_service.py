import subprocess
import base64
import time
import json
import uuid
from ldap3 import Server, Connection, ALL, SUBTREE
from app.core.config import get_primary_server
from app.services.ad_service import _get_admin_connection, _get_search_base

def get_all_devices():
    """Busca todos los computadores en el Active Directory."""
    conn = _get_admin_connection()
    search_base = _get_search_base()
    
    # Atributos a extraer
    attributes = ['dNSHostName', 'operatingSystem', 'description', 'lastLogonTimestamp', 'sAMAccountName']
    
    conn.search(
        search_base=search_base,
        search_filter='(&(objectCategory=computer))',
        search_scope=SUBTREE,
        attributes=attributes
    )
    
    devices = []
    for entry in conn.entries:
        # Formatear el timestamp
        last_logon = "N/A"
        if entry.lastLogonTimestamp:
            try:
                last_logon = entry.lastLogonTimestamp.value.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
                
        hostname = str(entry.dNSHostName) if entry.dNSHostName else str(entry.sAMAccountName).replace('$', '')
        
        devices.append({
            "hostname": hostname,
            "os": str(entry.operatingSystem) if entry.operatingSystem else "Desconocido",
            "description": str(entry.description) if entry.description else "",
            "last_logon": last_logon,
            "status": "unknown" # Se puede actualizar luego con Ping en lote si se desea
        })
        
    # Ordenar alfabéticamente por hostname
    return sorted(devices, key=lambda x: x["hostname"].lower())

def ping_device(hostname: str) -> bool:
    """Realiza un ping rápido (1 paquete, timeout corto) al equipo."""
    # En Windows, -n 1 es un ping, -w 1000 es timeout en ms
    res = subprocess.run(["ping", "-n", "1", "-w", "1000", hostname], capture_output=True, text=True)
    if "TTL=" in res.stdout:
        return True
    return False

def _execute_wmi_on_device(hostname: str, script: str) -> str:
    """Ejecuta un script de PowerShell remotamente en el equipo cliente usando WMI."""
    try:
        cfg = get_primary_server("da")
    except Exception as e:
        raise ValueError(str(e))
        
    admin_user = cfg["admin_user"]
    admin_pass = cfg["admin_pass"]
    safe_pass = admin_pass.replace("'", "''")
    
    guid = str(uuid.uuid4())
    remote_path = f"C:\\Windows\\Temp\\{guid}.json"
    
    wrapped_script = f"""
    $ErrorActionPreference = 'Stop'
    try {{
        $result = & {{
            {script}
        }}
        if ($null -eq $result) {{
            [System.IO.File]::WriteAllText('{remote_path}', 'SUCCESS')
        }} elseif ($result -is [array] -or $result -is [PSCustomObject] -or $result -is [System.Management.Automation.PSCustomObject]) {{
            $json = $result | ConvertTo-Json -Compress
            [System.IO.File]::WriteAllText('{remote_path}', $json)
        }} else {{
            [System.IO.File]::WriteAllText('{remote_path}', [string]$result)
        }}
    }} catch {{
        [System.IO.File]::WriteAllText('{remote_path}', "ERROR: " + $_.Exception.Message)
    }}
    """
    
    encoded = base64.b64encode(wrapped_script.encode('utf-16le')).decode('utf-8')
    cmd = f"powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand {encoded}"
    
    wmi_script = f"""
    $password = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
    $cred = New-Object System.Management.Automation.PSCredential ('{admin_user}', $password)
    $res = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList '{cmd}' -ComputerName '{hostname}' -Credential $cred
    if ($res.ReturnValue -ne 0) {{
        throw "WMI Error: ReturnValue $($res.ReturnValue)"
    }}
    """
    
    # 1. Establecer conexión IPC$ para leer luego el archivo
    target_smb = f"\\\\{hostname}\\IPC$"
    subprocess.run(["net", "use", target_smb, "/delete", "/y"], capture_output=True)
    smb_conn = subprocess.run(["net", "use", target_smb, admin_pass, f"/user:{admin_user}"], capture_output=True, text=True)
    if smb_conn.returncode != 0:
        error_msg = smb_conn.stderr.replace(admin_pass, "********")
        raise Exception(f"No se pudo conectar vía SMB al equipo {hostname}: {error_msg}. ¿Está encendido?")

    # 2. Ejecutar WMI
    wmi_res = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", wmi_script],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    if wmi_res.returncode != 0:
        error_msg = wmi_res.stderr.strip() if wmi_res.stderr else wmi_res.stdout.strip()
        error_msg = error_msg.replace(safe_pass, "********").replace(admin_pass, "********")
        raise Exception(f"Error ejecutando WMI en {hostname}: {error_msg}")
        
    # 3. Leer archivo
    unc_file_path = f"\\\\{hostname}\\C$\\Windows\\Temp\\{guid}.json"
    output = ""
    for _ in range(15):
        time.sleep(1)
        check = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", f"if (Test-Path '{unc_file_path}') {{ Get-Content '{unc_file_path}' -Raw; Remove-Item '{unc_file_path}' -Force }}"], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if check.returncode == 0 and check.stdout.strip():
            output = check.stdout.strip()
            break
            
    if not output:
        raise Exception(f"Timeout esperando respuesta de {hostname}.")
        
    if output.startswith("ERROR: "):
        raise Exception(f"Error Remoto: {output[7:]}")
        
    if output == "SUCCESS":
        return ""
        
    return output

def reboot_device(hostname: str):
    """Reinicia un computador remotamente usando el comando nativo."""
    # Alternativamente podemos usar WMI: (Get-WmiObject -Class Win32_OperatingSystem -ComputerName ...).Reboot()
    script = "Restart-Computer -Force"
    _execute_wmi_on_device(hostname, script)
    return True

def get_bitlocker_status(hostname: str):
    """Consulta el estado de cifrado de BitLocker en la unidad C:"""
    script = """
    $vol = Get-BitLockerVolume -MountPoint 'C:'
    if ($vol) {
        [PSCustomObject]@{
            VolumeStatus = $vol.VolumeStatus.ToString()
            EncryptionPercentage = $vol.EncryptionPercentage
            ProtectionStatus = $vol.ProtectionStatus.ToString()
        }
    } else {
        "NO_BITLOCKER"
    }
    """
    out = _execute_wmi_on_device(hostname, script)
    if out == "NO_BITLOCKER":
        return None
    try:
        return json.loads(out)
    except:
        return out
