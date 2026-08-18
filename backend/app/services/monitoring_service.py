import subprocess
import base64
import time
import json
import uuid
import concurrent.futures
import logging
from app.models.server import ServerConfig
from app.core.encryption import decrypt_password
from app.core.database import SessionLocal

import tempfile
import os

logger = logging.getLogger(__name__)

_server_stats_cache = {}

# ── Timeout máximo por servidor en el pool de threads (segundos) ─────────────
_WORKER_TIMEOUT = 30


def get_server_stats(server: ServerConfig):
    """Entry point unificado: enruta al servicio correcto según os_type."""
    try:
        os_type = getattr(server, "os_type", "windows") or "windows"
        if os_type == "linux":
            from app.services.linux_monitoring_service import get_linux_stats
            return get_linux_stats(server)
        else:
            return _get_server_stats_internal(server)
    except Exception as e:
        return {"status": "error", "error": f"Internal Error: {e}"}


def get_top_processes(server: ServerConfig) -> list:
    """Obtiene el Top 5 de procesos bajo demanda según el OS del servidor."""
    try:
        os_type = getattr(server, "os_type", "windows") or "windows"
        if os_type == "linux":
            from app.services.linux_monitoring_service import get_linux_top_processes
            return get_linux_top_processes(server)
        else:
            return _get_windows_top_processes(server)
    except Exception as e:
        logger.warning(f"[Top Processes] Error en {server.ip}: {e}")
        return []


def _get_windows_top_processes(server: ServerConfig) -> list:
    """Obtiene el Top 5 de procesos en un servidor Windows via PowerShell remoto."""
    ip = server.ip
    admin_user = server.admin_user
    admin_pass = decrypt_password(server.admin_pass)

    domain = server.domain
    if domain and "\\" not in admin_user and "@" not in admin_user:
        admin_user = f"{domain}\\{admin_user}"

    safe_pass = admin_pass.replace("'", "''")

    # Script PowerShell que extrae Top 5 por CPU
    ps_script = """
    $procs = Get-Process | Where-Object {$_.CPU -gt 0} | Sort-Object CPU -Descending | Select-Object -First 5
    $result = $procs | ForEach-Object {
        $uptime = 1
        if ($_.StartTime) {
            $uptime = [math]::Max(1, ((Get-Date) - $_.StartTime).TotalSeconds)
        }
        $cpuPercent = [math]::Round($_.CPU / $uptime * 100, 1)
        $memMb = [math]::Round($_.WorkingSet64 / 1MB, 1)
        [PSCustomObject]@{
            pid = $_.Id
            name = $_.ProcessName
            cpu_percent = $cpuPercent
            mem_percent = $memMb
        }
    }
    $result | ConvertTo-Json -Compress
    """

    import socket

    def is_local_ip(target_ip):
        if target_ip in ["127.0.0.1", "localhost", "::1"]:
            return True
        try:
            return target_ip in [i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None)]
        except Exception:
            return False

    try:
        if is_local_ip(ip):
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15
            )
            raw = res.stdout.strip()
        else:
            import uuid
            import time
            import base64
            guid = str(uuid.uuid4())
            remote_path = f"C:\\Windows\\Temp\\{guid}.json"
            
            wrapped_script = f"""
            $ErrorActionPreference = 'Stop'
            try {{
                $result = & {{ {ps_script} }}
                [System.IO.File]::WriteAllText('{remote_path}', $result)
            }} catch {{
                [System.IO.File]::WriteAllText('{remote_path}', "ERROR: " + $_.Exception.Message)
            }}
            """
            
            encoded = base64.b64encode(wrapped_script.encode('utf-16le')).decode('utf-8')
            cmd = f"powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand {encoded}"
            
            wmi_script = f"""
            $password = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
            $cred = New-Object System.Management.Automation.PSCredential ('{admin_user}', $password)
            $res = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList '{cmd}' -ComputerName '{ip}' -Credential $cred
            if ($res.ReturnValue -ne 0) {{ throw "WMI Error: ReturnValue $($res.ReturnValue)" }}
            """
            
            target_smb = f"\\\\{ip}\\IPC$"
            subprocess.run(["net", "use", target_smb, "/delete", "/y"], capture_output=True)
            smb_conn = subprocess.run(
                ["net", "use", target_smb, admin_pass, f"/user:{admin_user}"],
                capture_output=True, text=True, timeout=10
            )
            if smb_conn.returncode != 0:
                logger.warning(f"[Windows Processes] SMB Error {ip}: {smb_conn.stderr}")
                return []
                
            wmi_res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "-"],
                input=wmi_script, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=20
            )
            
            if wmi_res.returncode != 0:
                logger.warning(f"[Windows Processes] WMI Error {ip}: {wmi_res.stderr or wmi_res.stdout}")
                return []
                
            unc_file_path = f"\\\\{ip}\\C$\\Windows\\Temp\\{guid}.json"
            raw = ""
            for _ in range(15):
                time.sleep(1)
                check = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", 
                     f"if (Test-Path '{unc_file_path}') {{ Get-Content '{unc_file_path}' -Raw; Remove-Item '{unc_file_path}' -Force }}"], 
                    capture_output=True, text=True, encoding='utf-8', errors='replace'
                )
                if check.returncode == 0 and check.stdout.strip():
                    raw = check.stdout.strip()
                    break
                    
            if not raw or raw.startswith("ERROR: "):
                logger.warning(f"[Windows Processes] Fetch Error {ip}: {raw}")
                return []

        if not raw:
            return []

        data = json.loads(raw)
        # json.loads puede retornar dict si solo hay un proceso
        if isinstance(data, dict):
            data = [data]

        return [
            {
                "pid": int(item.get("pid") or 0),
                "name": str(item.get("name") or "")[:30],
                "cpu_percent": float(item.get("cpu_percent") or 0),
                "mem_percent": float(item.get("mem_percent") or 0),
            }
            for item in data
        ][:5]

    except Exception as e:
        logger.warning(f"[Windows Processes] Error en {ip}: {e}")
        return []


def _get_server_stats_internal(server: ServerConfig):
    """Obtiene métricas de CPU, RAM y Disco del servidor Windows usando WMI nativo a través del túnel SMB."""
    ip = server.ip
    domain = server.domain
    admin_user = server.admin_user
    admin_pass = decrypt_password(server.admin_pass)
    
    if domain and "\\" not in admin_user and "@" not in admin_user:
        admin_user = f"{domain}\\{admin_user}"
        
    safe_pass = admin_pass.replace("'", "''")
    guid = str(uuid.uuid4())
    remote_path = f"C:\\Windows\\Temp\\{guid}.json"
    
    # Script que saca los porcentajes
    script = """
    $cpu = Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average
    $ram = Get-WmiObject Win32_OperatingSystem
    $ramTotal = [math]::Round($ram.TotalVisibleMemorySize / 1MB, 2)
    $ramFree = [math]::Round($ram.FreePhysicalMemory / 1MB, 2)
    $ramUsed = $ramTotal - $ramFree
    $ramPerc = [math]::Round(($ramUsed / $ramTotal) * 100, 1)
    
    $disks = @(Get-WmiObject Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID, 
        @{Name='SizeGB';Expression={[math]::Round($_.Size / 1GB, 2)}},
        @{Name='FreeGB';Expression={[math]::Round($_.FreeSpace / 1GB, 2)}})
        
    $uptime = (Get-Date) - $ram.ConvertToDateTime($ram.LastBootUpTime)
    
    [PSCustomObject]@{
        CPU = if ($cpu) { $cpu } else { 0 }
        RAM_Total = $ramTotal
        RAM_Used = $ramUsed
        RAM_Percent = $ramPerc
        Disks = $disks
        UptimeDays = $uptime.Days
        UptimeHours = $uptime.Hours
    }
    """
    
    import socket
    
    def is_local_ip(target_ip):
        if target_ip in ["127.0.0.1", "localhost", "::1"]: return True
        try:
            return target_ip in [i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None)]
        except:
            return False

    if is_local_ip(ip):
        # Ejecutar localmente sin WMI ni credenciales (es el propio servidor)
        local_res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if local_res.returncode != 0:
            return {"status": "error", "error": local_res.stderr}
        try:
            data = json.loads(local_res.stdout)
            data["status"] = "online"
            return data
        except Exception as e:
            return {"status": "error", "error": f"Error parseando JSON local: {e}"}

    # EJECUCIÓN REMOTA
    wrapped_script = f"""
    $ErrorActionPreference = 'Stop'
    try {{
        $result = & {{ {script} }}
        $json = $result | ConvertTo-Json -Compress
        [System.IO.File]::WriteAllText('{remote_path}', $json)
    }} catch {{
        [System.IO.File]::WriteAllText('{remote_path}', "ERROR: " + $_.Exception.Message)
    }}
    """
    
    encoded = base64.b64encode(wrapped_script.encode('utf-16le')).decode('utf-8')
    cmd = f"powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand {encoded}"
    
    wmi_script = f"""
    $password = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
    $cred = New-Object System.Management.Automation.PSCredential ('{admin_user}', $password)
    $res = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList '{cmd}' -ComputerName '{ip}' -Credential $cred
    if ($res.ReturnValue -ne 0) {{ throw "WMI Error: ReturnValue $($res.ReturnValue)" }}
    """
    
    target_smb = f"\\\\{ip}\\IPC$"
    subprocess.run(["net", "use", target_smb, "/delete", "/y"], capture_output=True)
    smb_conn = subprocess.run(["net", "use", target_smb, admin_pass, f"/user:{admin_user}"], capture_output=True, text=True)
    if smb_conn.returncode != 0:
        return {"status": "offline", "error": smb_conn.stderr.replace(admin_pass, "********")}
        
    wmi_res = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "-"],
        input=wmi_script,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
        
    if wmi_res.returncode != 0:
        err = (wmi_res.stderr or wmi_res.stdout).replace(admin_pass, "********").replace(safe_pass, "********")
        return {"status": "error", "error": err}
        
    unc_file_path = f"\\\\{ip}\\C$\\Windows\\Temp\\{guid}.json"
    output = ""
    for _ in range(15):
        time.sleep(1)
        check = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", f"if (Test-Path '{unc_file_path}') {{ Get-Content '{unc_file_path}' -Raw; Remove-Item '{unc_file_path}' -Force }}"], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if check.returncode == 0 and check.stdout.strip():
            output = check.stdout.strip()
            break
            
    if not output:
        return {"status": "timeout", "error": "Timeout WMI"}
    if output.startswith("ERROR: "):
        return {"status": "error", "error": output[7:]}
        
    try:
        data = json.loads(output)
        data["status"] = "online"
        return data
    except Exception as e:
        return {"status": "error", "error": str(e)}

def sync_monitoring_stats():
    """Ejecutado por APScheduler cada minuto para mantener el caché caliente."""
    global _server_stats_cache
    db = SessionLocal()
    try:
        servers = db.query(ServerConfig).all()
        new_cache = {}
        
        # Run sequentially or with a ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_srv = {executor.submit(get_server_stats, srv): srv for srv in servers}
            for future in concurrent.futures.as_completed(future_to_srv, timeout=_WORKER_TIMEOUT * len(servers) + 10):
                srv = future_to_srv[future]
                try:
                    stats = future.result(timeout=_WORKER_TIMEOUT)
                    
                    old_data = _server_stats_cache.get(srv.id, {})
                    old_hist = old_data.get("history", {"cpu": [0]*20, "ram": [0]*20})
                    
                    history = {
                        "cpu": list(old_hist["cpu"]),
                        "ram": list(old_hist["ram"])
                    }
                    
                    if stats.get("status") == "online":
                        history["cpu"].append(stats.get("CPU", 0))
                        if len(history["cpu"]) > 20:
                            history["cpu"].pop(0)
                            
                        history["ram"].append(stats.get("RAM_Percent", 0))
                        if len(history["ram"]) > 20:
                            history["ram"].pop(0)

                    new_cache[srv.id] = {
                        "id": srv.id,
                        "name": srv.name,
                        "type": srv.server_type,
                        "os_type": getattr(srv, "os_type", "windows") or "windows",
                        "ip": srv.ip,
                        "stats": stats,
                        "history": history
                    }
                except concurrent.futures.TimeoutError:
                    # Este servidor tardó demasiado — no bloquea a los demás
                    old_data = _server_stats_cache.get(srv.id, {})
                    new_cache[srv.id] = {
                        **old_data,
                        "stats": {"status": "timeout", "error": "Worker timeout"},
                    }
                except Exception as e:
                    logger.warning(f"[Sync] Error procesando {srv.name}: {e}")
                    
        _server_stats_cache = new_cache
    finally:
        db.close()

def get_cached_monitoring_stats():
    """Retorna los datos del caché en memoria instantáneamente."""
    return list(_server_stats_cache.values())
