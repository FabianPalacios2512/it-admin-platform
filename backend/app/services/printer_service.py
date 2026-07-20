import subprocess
import json
import uuid
import time
import base64
from app.core.config import get_primary_server

_printers_cache = {"time": 0, "data": None}
_PRINTERS_CACHE_TTL = 30

def invalidate_printers_cache():
    global _printers_cache
    _printers_cache["time"] = 0

def _execute_remote_ps(script: str) -> str:
    """Ejecuta un bloque de script PowerShell en el servidor de impresoras remotamente."""
    try:
        cfg = get_primary_server("printers")
    except Exception as e:
        raise ValueError(str(e))
    
    ip = cfg["ip"]
    domain = cfg.get("domain", "")
    admin_user = cfg["admin_user"]
    admin_pass = cfg["admin_pass"]

    # Asegurar el formato de dominio
    if domain and "\\" not in admin_user and "@" not in admin_user:
        admin_user = f"{domain}\\{admin_user}"

    # Escapar comillas en la contraseña para evitar inyección
    safe_pass = admin_pass.replace("'", "''")

    guid = str(uuid.uuid4())
    remote_path = f"C:\\Windows\\Temp\\{guid}.json"
    remote_ps1 = f"C:\\Windows\\Temp\\{guid}.ps1"
    
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
    
    # Write the script to the remote server via SMB
    unc_ps1_path = f"\\\\{ip}\\C$\\Windows\\Temp\\{guid}.ps1"
    # Wait, we need to connect to SMB first before we can write the file!


    # Mount SMB First to write the file
    target_smb = f"\\\\{ip}\\IPC$"
    target_c = f"\\\\{ip}\\C$"
    subprocess.run(["net", "use", target_smb, "/delete", "/y"], capture_output=True)
    subprocess.run(["net", "use", target_c, "/delete", "/y"], capture_output=True)
    smb_conn = subprocess.run(["net", "use", target_smb, admin_pass, f"/user:{admin_user}"], capture_output=True, text=True)
    c_conn = subprocess.run(["net", "use", target_c, admin_pass, f"/user:{admin_user}"], capture_output=True, text=True)
    if smb_conn.returncode != 0 and c_conn.returncode != 0:
        error_msg = smb_conn.stderr.replace(admin_pass, "********")
        raise Exception(f"Failed to connect to SMB: {error_msg}")

    # Write .ps1 to remote Temp dir
    try:
        with open(unc_ps1_path, "w", encoding="utf-8-sig") as f:
            f.write(wrapped_script)
    except Exception as e:
        raise Exception(f"Failed to write PS1 script to {unc_ps1_path}: {e}")

    cmd = f"powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File {remote_ps1}"
    
    wmi_script = f"""
    $password = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
    $cred = New-Object System.Management.Automation.PSCredential ('{admin_user}', $password)
    $res = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList '{cmd}' -ComputerName '{ip}' -Credential $cred
    if ($res.ReturnValue -ne 0) {{
        throw "WMI Error: ReturnValue $($res.ReturnValue)"
    }}
    """

    wmi_res = subprocess.run(
        [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile", "-NonInteractive", "-Command", wmi_script],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        shell=True
    )

    if wmi_res.returncode != 0:
        error_msg = wmi_res.stderr.strip() if wmi_res.stderr else wmi_res.stdout.strip()
        error_msg = error_msg.replace(safe_pass, "********").replace(admin_pass, "********")
        raise Exception(f"Error de WMI: {error_msg}")

    import os
    unc_file_path = f"\\\\{ip}\\C$\\Windows\\Temp\\{guid}.json"
    output = ""
    for _ in range(60):
        time.sleep(0.5)
        if os.path.exists(unc_file_path):
            try:
                with open(unc_file_path, "r", encoding="utf-8-sig", errors="replace") as f:
                    content = f.read().strip()
                if content:
                    output = content
                    try:
                        os.remove(unc_file_path)
                    except Exception:
                        pass
                    break
            except Exception:
                pass

    try:
        if os.path.exists(unc_ps1_path):
            os.remove(unc_ps1_path)
    except Exception:
        pass

    if not output:
        raise Exception("Timeout esperando respuesta del script remoto (WMI).")

    if output.startswith("ERROR: "):
        raise Exception(f"PowerShell Error: {output[7:]}")

    if output == "SUCCESS":
        return ""

    return output

def get_printers():
    """Obtiene la lista de impresoras usando RPC nativo (win32print) evitando WMI."""
    global _printers_cache
    if time.time() - _printers_cache["time"] < _PRINTERS_CACHE_TTL and _printers_cache["data"] is not None:
        return _printers_cache["data"]
        
    try:
        cfg = get_primary_server("printers")
    except Exception:
        return []
        
    ip = cfg["ip"]
    admin_user = cfg["admin_user"]
    admin_pass = cfg["admin_pass"]
    domain = cfg.get("domain", "")
    
    if domain and "\\" not in admin_user and "@" not in admin_user:
        admin_user = f"{domain}\\{admin_user}"

    # Autenticar vía SMB/RPC
    target_smb = f"\\\\{ip}\\IPC$"
    subprocess.run(["net", "use", target_smb, "/delete", "/y"], capture_output=True)
    subprocess.run(["net", "use", target_smb, admin_pass, f"/user:{admin_user}"], capture_output=True)

    try:
        import win32print
        # Nivel 2 trae Name, PortName, DriverName, ShareName, Attributes
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_NAME, f"\\\\{ip}", 2)
        
        resultList = []
        for p in printers:
            name = p.get('pPrinterName', '')
            if '\\' in name:
                name = name.split('\\')[-1]
                
            # PRINTER_ATTRIBUTE_SHARED = 8
            shared = (p.get('Attributes', 0) & 8) != 0
            
            resultList.append({
                "Name": name,
                "PortName": p.get('pPortName', ''),
                "IPAddress": p.get('pPortName', ''),
                "Shared": shared,
                "ShareName": p.get('pShareName', ''),
                "DriverName": p.get('pDriverName', '')
            })
            
        _printers_cache["data"] = resultList
        _printers_cache["time"] = time.time()
        return resultList
    except Exception as e:
        print(f"Error nativo leyendo impresoras de {ip}: {e}")
        return []

def get_drivers():
    """Obtiene los controladores instalados."""
    script = """
    Get-PrinterDriver | Select-Object Name
    """
    output = _execute_remote_ps(script)
    if not output:
        return []
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            return [data["Name"]]
        return [d["Name"] for d in data if "Name" in d]
    except Exception:
        return []

def add_printer(name: str, ip: str, driver: str, shared: bool, share_name: str):
    """Crea un puerto TCP/IP y luego la impresora."""
    port_name = f"IP_{ip}"
    shared_str = "$true" if shared else "$false"
    share_name_arg = f"-ShareName '{share_name}'" if shared and share_name else ""
    
    script = f"""
    # 1. Crear puerto si no existe
    $portExists = Get-PrinterPort -Name '{port_name}' -ErrorAction SilentlyContinue
    if (-not $portExists) {{
        Add-PrinterPort -Name '{port_name}' -PrinterHostAddress '{ip}'
    }}
    
    # 2. Crear Impresora
    Add-Printer -Name '{name}' -DriverName '{driver}' -PortName '{port_name}' -Shared:{shared_str} {share_name_arg}
    """
    _execute_remote_ps(script)
    invalidate_printers_cache()

def update_printer_ip(old_name: str, new_name: str, new_ip: str, shared: bool, share_name: str):
    """Re-enruta la IP (crea puerto nuevo y lo asigna) y renombra."""
    port_name = f"IP_{new_ip}"
    shared_str = "$true" if shared else "$false"
    share_name_arg = f"-ShareName '{share_name}'" if shared and share_name else ""
    
    script = f"""
    # 1. Crear nuevo puerto si no existe
    $portExists = Get-PrinterPort -Name '{port_name}' -ErrorAction SilentlyContinue
    if (-not $portExists) {{
        Add-PrinterPort -Name '{port_name}' -PrinterHostAddress '{new_ip}'
    }}
    
    # 2. Actualizar el puerto y la configuracion de red de la impresora actual
    Set-Printer -Name '{old_name}' -PortName '{port_name}' -Shared:{shared_str} {share_name_arg}
    
    # 3. Renombrar si hubo cambio
    if ('{old_name}' -ne '{new_name}') {{
        Rename-Printer -Name '{old_name}' -NewName '{new_name}'
    }}
    """
    _execute_remote_ps(script)
    invalidate_printers_cache()

def clear_spooler(name: str):
    """Limpia los trabajos de impresión atascados para esta impresora."""
    script = f"Get-PrintJob -PrinterName '{name}' | Remove-PrintJob"
    _execute_remote_ps(script)

def print_test_page(name: str):
    """Imprime una página de prueba de Windows."""
    script = f"""
    $printer = Get-CimInstance Win32_Printer -Filter "Name='{name}'"
    if ($printer) {{
        Invoke-CimMethod -InputObject $printer -MethodName PrintTestPage
    }} else {{
        throw "Impresora no encontrada"
    }}
    """
    _execute_remote_ps(script)

def delete_printer(name: str):
    """Elimina la impresora de forma segura."""
    script = f"Remove-Printer -Name '{name}'"
    _execute_remote_ps(script)
    invalidate_printers_cache()

def restart_spooler():
    """Reinicia el servicio Print Spooler en el servidor remoto."""
    script = "Restart-Service -Name Spooler -Force"
    _execute_remote_ps(script)

def generate_mapping_script(name: str) -> str:
    """Genera un script de PowerShell para mapear la impresora compartida."""
    printers = get_printers()
    printer = next((p for p in printers if p.get("Name") == name), None)
    
    if not printer:
        raise ValueError("Impresora no encontrada.")
    if not printer.get("Shared"):
        raise ValueError("La impresora no está compartida en red.")
        
    cfg = get_primary_server("printers")
    server_host = cfg["ip"]
    share_name = printer.get("ShareName")
    
    script = f"""# Script para mapear impresora {name}
$PrinterPath = "\\\\{server_host}\\{share_name}"
Write-Host "Conectando a $PrinterPath..."
Add-Printer -ConnectionName $PrinterPath
Write-Host "Impresora mapeada exitosamente."
"""
    return script


def get_printer_jobs(name: str):
    """Obtiene los trabajos en la cola de impresión de la impresora especificada usando win32print."""
    try:
        cfg = get_primary_server("printers")
    except Exception:
        raise ValueError("Servidor de impresoras no configurado.")
        
    ip = cfg["ip"]
    admin_user = cfg["admin_user"]
    admin_pass = cfg["admin_pass"]
    domain = cfg.get("domain", "")
    
    if domain and "\\" not in admin_user and "@" not in admin_user:
        admin_user = f"{domain}\\{admin_user}"

    # Autenticar vía SMB/RPC
    target_smb = f"\\\\{ip}\\IPC$"
    import subprocess
    subprocess.run(["net", "use", target_smb, "/delete", "/y"], capture_output=True)
    subprocess.run(["net", "use", target_smb, admin_pass, f"/user:{admin_user}"], capture_output=True)

    try:
        import win32print
        printer_path = f"\\\\{ip}\\{name}"
        hprinter = win32print.OpenPrinter(printer_path)
        
        # Level 2 properties: JobId, pUserName, pDocument, Status, TotalPages, Size, Submitted, pStatus
        jobs = win32print.EnumJobs(hprinter, 0, 100, 2)
        win32print.ClosePrinter(hprinter)
        
        resultList = []
        for j in jobs:
            
            # Formatear la fecha/hora
            submitted_str = ""
            if j.get("Submitted"):
                try:
                    # pywintypes.datetime
                    submitted_str = j["Submitted"].strftime("%Y-%m-%d %H:%M:%S")
                except:
                    submitted_str = str(j["Submitted"])
                    
            # Mapeo básico de estado (Status bits)
            status_code = j.get("Status", 0)
            status_text = j.get("pStatus") or "En cola"
            
            if status_code & win32print.JOB_STATUS_ERROR:
                status_text = "Error"
            elif status_code & win32print.JOB_STATUS_OFFLINE:
                status_text = "Fuera de línea"
            elif status_code & win32print.JOB_STATUS_PAPEROUT:
                status_text = "Sin papel"
            elif status_code & win32print.JOB_STATUS_PAUSED:
                status_text = "Pausado"
            elif status_code & win32print.JOB_STATUS_PRINTING:
                status_text = "Imprimiendo"
            elif status_code & win32print.JOB_STATUS_DELETING:
                status_text = "Eliminando"
                
            resultList.append({
                "JobId": j.get("JobId"),
                "User": j.get("pUserName", "Desconocido"),
                "Document": j.get("pDocument", "Documento sin título"),
                "Status": status_text,
                "Pages": j.get("TotalPages", 0),
                "Size": j.get("Size", 0),
                "Submitted": submitted_str
            })
            
        return resultList
    except Exception as e:
        raise ValueError(f"Error nativo obteniendo trabajos de {name}: {e}")

