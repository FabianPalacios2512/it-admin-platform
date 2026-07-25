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

def _run_invoke_command(script_block: str, return_json: bool = False):
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
    safe_pass = admin_pass.replace("'", "''")
    
    json_cmd = " | ConvertTo-Json -Compress" if return_json else ""
    
    ps_script = f"""
    $ErrorActionPreference = 'Stop'
    $password = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
    $cred = New-Object System.Management.Automation.PSCredential ('{admin_user}', $password)
    
    Invoke-Command -ComputerName '{ip}' -Credential $cred -ScriptBlock {{
        {script_block}
    }}{json_cmd}
    """
    import subprocess
    res = subprocess.run(
        [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if res.returncode != 0:
        error_msg = res.stderr.strip() if res.stderr else res.stdout.strip()
        raise Exception(f"PowerShell Error: {error_msg}")
    return res.stdout.strip()

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
            
            port_name = p.get('pPortName', '')
            ip_address = port_name
            if ip_address.startswith("IP_"):
                ip_address = ip_address[3:]
            
            resultList.append({
                "Name": name,
                "PortName": port_name,
                "IPAddress": ip_address,
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
    Get-PrinterDriver | Select-Object -ExpandProperty Name
    """
    try:
        output = _run_invoke_command(script, return_json=True)
        if not output:
            return []
        import json
        data = json.loads(output)
        if isinstance(data, list):
            return [d.get("value") for d in data if isinstance(d, dict) and "value" in d]
        elif isinstance(data, dict):
            return [data.get("value")]
        return []
    except Exception as e:
        print(f"Error cargando drivers: {e}")
        return []

def add_printer(name: str, ip: str, driver: str, shared: bool, share_name: str):
    """Crea un puerto TCP/IP y luego la impresora."""
    port_name = f"IP_{ip}"
    shared_str = "$true" if shared else "$false"
    share_name_arg = f"-ShareName '{share_name}'" if shared and share_name else ""
    
    script = f"""
    # 1. Crear nuevo puerto TCP/IP si no existe (usamos WMI para evitar el bloqueo de 2 minutos y desactivar SNMP)
    $portExists = Get-PrinterPort -Name '{port_name}' -ErrorAction SilentlyContinue
    if (-not $portExists) {{
        Set-WmiInstance -Class Win32_TCPIPPrinterPort -Arguments @{{ Name="{port_name}"; HostAddress="{ip}"; PortNumber=9100; Protocol=1; SNMPEnabled=0 }} | Out-Null
    }}
    
    # 2. Crear Impresora
    Add-Printer -Name '{name}' -DriverName '{driver}' -PortName '{port_name}' -Shared:{shared_str} {share_name_arg}
    """
    _run_invoke_command(script)
    invalidate_printers_cache()

def update_printer_ip(old_name: str, new_name: str, new_ip: str, new_driver: str, shared: bool, share_name: str):
    """Re-enruta la IP (crea puerto nuevo y lo asigna), cambia nombre y driver sin script dropping."""
    try:
        cfg = get_primary_server("printers")
    except Exception:
        raise ValueError("Servidor no configurado.")

    port_name = f"IP_{new_ip}"
    shared_str = "$true" if shared else "$false"
    share_name_arg = f"-ShareName '{share_name}'" if shared and share_name else ""
    driver_arg = f"-DriverName '{new_driver}'" if new_driver else ""
    
    script = f"""
    # 1. Crear nuevo puerto TCP/IP si no existe (usamos WMI para evitar timeout y desactivar SNMP)
    $portExists = Get-PrinterPort -Name '{port_name}' -ErrorAction SilentlyContinue
    if (-not $portExists) {{
        Set-WmiInstance -Class Win32_TCPIPPrinterPort -Arguments @{{ Name="{port_name}"; HostAddress="{new_ip}"; PortNumber=9100; Protocol=1; SNMPEnabled=0 }} | Out-Null
    }}
    
    # 2. Renombrar si es distinto
    if ('{old_name}' -ne '{new_name}') {{
        Rename-Printer -Name '{old_name}' -NewName '{new_name}'
    }}
    
    # 3. Asignar nuevo puerto y driver
    Set-Printer -Name '{new_name}' -PortName '{port_name}' {driver_arg} -Shared:{shared_str} {share_name_arg}
    """
    _run_invoke_command(script)
    invalidate_printers_cache()

def clear_spooler(name: str):
    """Limpia los trabajos de impresión atascados para esta impresora."""
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

    import subprocess
    import win32print
    
    target_smb = f"\\\\{ip}\\IPC$"
    subprocess.run(["net", "use", target_smb, "/delete", "/y"], capture_output=True)
    subprocess.run(["net", "use", target_smb, admin_pass, f"/user:{admin_user}"], capture_output=True)

    try:
        printer_path = f"\\\\{ip}\\{name}"
        # Se requieren permisos completos para purgar
        defaults = {"DesiredAccess": win32print.PRINTER_ALL_ACCESS}
        hprinter = win32print.OpenPrinter(printer_path, defaults)
        
        # Purgar todos los trabajos (PRINTER_CONTROL_PURGE = 3)
        win32print.SetPrinter(hprinter, 0, None, 3)
        win32print.ClosePrinter(hprinter)
    except Exception as e:
        raise ValueError(f"Error nativo limpiando cola de {name}: {e}")

def print_test_page(name: str):
    """Imprime una página de prueba de Windows evitando dropping de archivos para evadir BitDefender."""
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

    safe_pass = admin_pass.replace("'", "''")

    # Script ejecutado localmente, enviando el comando WMI directo por red (CIM)
    ps_script = f"""
    $ErrorActionPreference = 'Stop'
    $password = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
    $cred = New-Object System.Management.Automation.PSCredential ('{admin_user}', $password)
    
    $session = New-CimSession -ComputerName '{ip}' -Credential $cred
    try {{
        $printer = Get-CimInstance Win32_Printer -CimSession $session -Filter "Name='{name}'"
        if ($printer) {{
            Invoke-CimMethod -InputObject $printer -MethodName PrintTestPage | Out-Null
        }} else {{
            throw "Impresora '{name}' no encontrada en el servidor remoto."
        }}
    }} finally {{
        Remove-CimSession $session
    }}
    """
    
    import subprocess
    res = subprocess.run(
        [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if res.returncode != 0:
        error_msg = res.stderr.strip() if res.stderr else res.stdout.strip()
        raise ValueError(f"Error imprimiendo página de prueba (CIM): {error_msg}")

def delete_printer(name: str):
    """Elimina la impresora de forma segura e instantánea usando WMI."""
    script = f"""
    $printer = Get-CimInstance Win32_Printer -Filter "Name='{name}'" -ErrorAction SilentlyContinue
    if ($printer) {{
        Remove-CimInstance -InputObject $printer -ErrorAction SilentlyContinue
    }}
    """
    _run_invoke_command(script)
    invalidate_printers_cache()

def restart_spooler():
    """Reinicia el servicio Print Spooler en el servidor remoto."""
    script = "Restart-Service -Name Spooler -Force"
    _run_invoke_command(script)

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

def get_printer_history(name: str, limit: int = 50):
    """Obtiene el historial de impresiones (Auditoría) leyendo el EventViewer."""
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

    safe_pass = admin_pass.replace("'", "''")
    
    ps_script = f"""
    $ErrorActionPreference = 'SilentlyContinue'
    $password = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
    $cred = New-Object System.Management.Automation.PSCredential ('{admin_user}', $password)
    
    Invoke-Command -ComputerName '{ip}' -Credential $cred -ScriptBlock {{
        $events = Get-WinEvent -FilterHashtable @{{LogName='Microsoft-Windows-PrintService/Operational'; Id=307}} -MaxEvents 1000 -ErrorAction SilentlyContinue
        if (-not $events) {{
            Write-Output "[]"
            return
        }}
        $result = @()
        foreach ($e in $events) {{
            if ($e.Properties[3].Value -match '{name}') {{
                $result += [PSCustomObject]@{{
                    Time = $e.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')
                    User = $e.Properties[2].Value
                    Document = $e.Properties[1].Value
                    Pages = $e.Properties[6].Value
                    Size = $e.Properties[5].Value
                }}
            }}
        }}
        $result | Select-Object -First {limit} | ConvertTo-Json -Compress
    }}
    """
    
    import subprocess
    import json
    res = subprocess.run(
        [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    out = res.stdout.strip()
    if not out or out == "[]":
        return []
        
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            return [data]
        return data
    except Exception:
        return []

