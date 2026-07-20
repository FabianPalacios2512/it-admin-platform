import subprocess
import logging
import json
from app.models.server import ServerConfig
from app.core.encryption import decrypt_password
from app.services.ad_service import get_user_profile
import os
import glob

logger = logging.getLogger(__name__)

# Caché en memoria para no saturar el AD en cada recarga
_ad_name_cache = {}

def get_ad_fullname(upn: str) -> str:
    upn_lower = upn.lower()
    if upn_lower in _ad_name_cache:
        return _ad_name_cache[upn_lower]
        
    try:
        profile = get_user_profile(upn)
        if profile and profile.get("fullName"):
            _ad_name_cache[upn_lower] = profile["fullName"]
            return profile["fullName"]
    except Exception as e:
        logger.error(f"Error fetching AD profile para {upn}: {e}")
        
    # Fallback al username si no se encuentra
    _ad_name_cache[upn_lower] = upn
    return upn

def establish_ipc_connection(server: ServerConfig, admin_pass: str):
    target = f"\\\\{server.ip}\\IPC$"
    subprocess.run(["net", "use", target, "/delete", "/y"], capture_output=True)
    res = subprocess.run(["net", "use", target, admin_pass, f"/user:{server.admin_user}"], capture_output=True, text=True)
    if res.returncode != 0:
        error_msg = res.stderr.replace(admin_pass, "********")
        raise Exception(f"Fallo conectando al IPC$: {error_msg}")

def get_unc_path(server_ip: str, local_path: str) -> str:
    if local_path.startswith("\\\\"):
        return local_path
    if ":" in local_path:
        drive, rest = local_path.split(":", 1)
        if rest.startswith("\\") or rest.startswith("/"):
            rest = rest[1:]
        return f"\\\\{server_ip}\\{drive}$\\{rest}"
    return local_path

def get_rds_sessions(server: ServerConfig, temp_path: str, file_prefix: str = "nova.xl"):
    admin_pass = decrypt_password(server.admin_pass)
    establish_ipc_connection(server, admin_pass)
    
    # 1. Obtener usuarios atrapados usando Python + Rutas UNC
    unc_path = get_unc_path(server.ip, temp_path)
    file_users = set()
    
    try:
        if not os.path.exists(unc_path):
            raise Exception(f"La ruta UNC no es accesible o no existe: {unc_path}")
            
        files = os.listdir(unc_path)
        if not files:
            raise Exception(f"La carpeta {unc_path} está vacía. No hay archivos.")
            
        matched = 0
        for f in files:
            if f.lower().endswith(".txt"):
                f = f[:-4]
            if f.lower().startswith(file_prefix.lower()):
                matched += 1
                username = f[len(file_prefix):].strip()
                if username:
                    file_users.add(username)
                    
        if matched == 0:
            sample = files[0] if files else "N/A"
            raise Exception(f"Hay {len(files)} archivos en la carpeta (ej: {sample}), pero ninguno utiliza tu prefijo actual ('{file_prefix}').")
            
    except Exception as e:
        logger.error(f"Error de lectura en {unc_path}: {e}")
        raise Exception(f"Error leyendo archivos: {e}")
    
    # 2. Obtener sesiones activas de qwinsta
    res_qw = subprocess.run(["qwinsta", f"/server:{server.ip}"], capture_output=True, text=True)
    qw_sessions = {}
    
    if res_qw.returncode == 0:
        lines = res_qw.stdout.strip().split("\n")
        if len(lines) > 1:
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    session_name = line[0:18].strip()
                    username = line[19:39].strip()
                    session_id = line[39:45].strip()
                    state = line[46:54].strip()
                    
                    if username and session_id.isdigit():
                        qw_sessions[username.lower()] = {
                            "session_id": session_id,
                            "session_name": session_name,
                            "state": state
                        }
    
    # 3. Fusionar datos (Prioridad a los archivos físicos)
    sessions_result = []
    
    for u in file_users:
        u_lower = u.lower()
        full_name = get_ad_fullname(u)
        qw_data = qw_sessions.get(u_lower)
        
        sessions_result.append({
            "username": u,
            "full_name": full_name,
            "session_id": qw_data["session_id"] if qw_data else None,
            "session_name": qw_data["session_name"] if qw_data else "N/A",
            "state": qw_data["state"] if qw_data else "Sin Sesión"
        })
        
    # Ordenar alfabéticamente por username
    sessions_result.sort(key=lambda x: x["username"].lower())
    
    return sessions_result

def kill_rds_session(server: ServerConfig, temp_path: str, session_id: str = None, username: str = None, file_prefix: str = "nova.xl"):
    admin_pass = decrypt_password(server.admin_pass)
    establish_ipc_connection(server, admin_pass)
    
    errors = []
    
    # 1. Matar sesión de Windows si existe
    if session_id:
        res = subprocess.run(["logoff", session_id, f"/server:{server.ip}"], capture_output=True, text=True)
        if res.returncode != 0:
            errors.append(f"Error logoff: {res.stderr or res.stdout}")
            
    # 2. Borrar archivo físico usando UNC
    if username and temp_path:
        unc_path = get_unc_path(server.ip, temp_path)
        try:
            if os.path.exists(unc_path):
                files = os.listdir(unc_path)
                target_prefix = f"{file_prefix}{username}".lower()
                for f in files:
                    # Chequear con y sin txt por si acaso
                    check_f = f.lower()
                    if check_f.endswith(".txt"):
                        check_f = check_f[:-4]
                    
                    if check_f.startswith(target_prefix):
                        os.remove(os.path.join(unc_path, f))
        except Exception as e:
            errors.append(f"Error borrando archivo por red: {e}")
            
    if errors:
        raise Exception(" | ".join(errors))
        
    return True

def clean_temp_folder(server: ServerConfig, temp_path: str, file_prefix: str = "nova.ft"):
    admin_pass = decrypt_password(server.admin_pass)
    unc_path = get_unc_path(server.ip, temp_path)
    try:
        if os.path.exists(unc_path):
            files = os.listdir(unc_path)
            for f in files:
                if f.lower().startswith(file_prefix.lower()):
                    os.remove(os.path.join(unc_path, f))
    except Exception as e:
        raise Exception(f"Error borrando temporales por UNC: {e}")
    return True

def execute_mass_cleanup(server: ServerConfig, temp_path: str, file_prefix: str = "nova.xl"):
    # Cierra todas las sesiones que tengan archivos
    sessions = get_rds_sessions(server, temp_path, file_prefix)
    for s in sessions:
        try:
            kill_rds_session(server, temp_path, s.get("session_id"), s.get("username"), file_prefix)
        except Exception as e:
            logger.error(f"Fallo al cerrar sesión de {s.get('username')}: {e}")
            
def _run_remote_ps(server: ServerConfig, script_block: str, timeout: int = 20):
    """Ejecuta un bloque de PowerShell en el servidor remoto usando Invoke-Command (WinRM)."""
    admin_pass = decrypt_password(server.admin_pass)
    
    # Construir el comando PowerShell que crea credenciales y ejecuta remotamente
    ps_cmd = f"""
$ErrorActionPreference = 'Stop'
# Registrar el servidor como equipo de confianza para WinRM si tenemos permisos
try {{
    $current = (Get-Item WSMan:\\localhost\\Client\\TrustedHosts -ErrorAction SilentlyContinue).Value
    if ($current -notlike '*{server.ip}*') {{
        Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '{server.ip}' -Force -Concatenate -ErrorAction Stop
    }}
}} catch {{
    # Si no somos administrador local, ignoramos. El usuario debera configurarlo manualmente.
}}
$pass = ConvertTo-SecureString '{admin_pass}' -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential('{server.admin_user}', $pass)
try {{
    $result = Invoke-Command -ComputerName '{server.ip}' -Credential $cred -ScriptBlock {{ {script_block} }} -ErrorAction Stop
    Write-Output $result
}} catch {{
    Write-Error $_.Exception.Message
    exit 1
}}
"""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return res
    except subprocess.TimeoutExpired:
        raise Exception(
            f"Tiempo agotado conectando a {server.ip}. "
            "Asegúrate de ejecutar esta App (backend) como Administrador en este equipo para autoconfigurar WinRM, "
            "o ejecuta manualmente: winrm quickconfig"
        )

def deploy_remote_task(server: ServerConfig, temp_path: str, file_prefix: str, cron_time: str, cron_days: str):
    admin_pass = decrypt_password(server.admin_pass)
    establish_ipc_connection(server, admin_pass)
    
    ps_script = f"""
$tempPath = "{temp_path}"
$filePrefix = "{file_prefix}"

$qwinstaOutput = qwinsta
$activeSessions = @{{}}
foreach ($line in $qwinstaOutput) {{
    if ($line -match '^>?(?<sessionname>.{{18}})\\s+(?<username>.{{20}})\\s+(?<id>.{{8}})\\s+(?<state>.{{8}})') {{
        $user = $matches.username.Trim().ToLower()
        $id = $matches.id.Trim()
        if ([int]::TryParse($id, [ref]0)) {{
            $activeSessions[$user] = $id
        }}
    }}
}}

if (Test-Path $tempPath) {{
    $files = Get-ChildItem -Path $tempPath -Filter "$($filePrefix)*"
    foreach ($f in $files) {{
        $name = $f.Name
        if ($name.ToLower().EndsWith(".txt")) {{
            $name = $name.Substring(0, $name.Length - 4)
        }}
        $username = $name.Substring($filePrefix.Length).Trim()
        if ($username -ne "") {{
            $userLower = $username.ToLower()
            if ($activeSessions.ContainsKey($userLower)) {{
                $sessionId = $activeSessions[$userLower]
                logoff $sessionId
            }}
            Remove-Item -Path $f.FullName -Force -ErrorAction SilentlyContinue
        }}
    }}
    Remove-Item -Path "$tempPath\\$filePrefix*" -Force -ErrorAction SilentlyContinue
}}
"""
    # 1. Copiar el script al servidor via UNC (esto ya funciona)
    admin_infra_path = get_unc_path(server.ip, "C:\\AdminInfra")
    if not os.path.exists(admin_infra_path):
        os.makedirs(admin_infra_path, exist_ok=True)
        subprocess.run(["attrib", "+h", admin_infra_path], capture_output=True)
        
    script_path = os.path.join(admin_infra_path, "rds_cleanup.ps1")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(ps_script.strip())
        
    # 2. Crear la tarea programada remotamente via Invoke-Command (WinRM)
    # Convertir días al formato de PowerShell (en inglés, ya que los cmdlets de PS usan enumeraciones en inglés siempre)
    DAY_MAP = {"0": "Monday", "1": "Tuesday", "2": "Wednesday", "3": "Thursday", "4": "Friday", "5": "Saturday", "6": "Sunday"}
    ps_days = ",".join([DAY_MAP.get(d.strip()) for d in cron_days.split(",") if d.strip() in DAY_MAP])
    
    # Primero intentar borrar la tarea vieja
    delete_remote_task(server)
    
    remote_block = f"""
$ErrorActionPreference = 'Stop'
$taskName = "AdminInfra_RDS_Cleanup"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-ExecutionPolicy Bypass -WindowStyle Hidden -File C:\\AdminInfra\\rds_cleanup.ps1'
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek {ps_days} -At '{cron_time}'
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -User 'SYSTEM' -Force | Out-Null
"""
    
    res = _run_remote_ps(server, remote_block, timeout=20)
    
    # Si WinRM falló o el script lanzó error
    if res.returncode != 0:
        error_msg = res.stderr.strip() if res.stderr else res.stdout.strip()
        error_msg = error_msg.replace(admin_pass, "********")
        raise Exception(f"Error creando tarea remota: {error_msg}")
        
    # Verificar si el output tiene algún error silencioso
    if "Error" in res.stdout or "Exception" in res.stdout:
        raise Exception(f"Error interno en PowerShell: {res.stdout.strip()}")
        
    logger.info(f"✅ Tarea programada creada en {server.ip}: {cron_time} dias={ps_days}")
    return True

def delete_remote_task(server: ServerConfig):
    try:
        _run_remote_ps(server, "schtasks /Delete /TN 'AdminInfra_RDS_Cleanup' /F 2>&1", timeout=15)
    except Exception:
        pass
    return True

def query_remote_task(server: ServerConfig):
    try:
        res = _run_remote_ps(server, "schtasks /Query /TN 'AdminInfra_RDS_Cleanup' /V /FO CSV", timeout=15)
        # DEBUG: Guardar salida para inspeccionar
        with open("debug.txt", "w", encoding="utf-8") as f:
            f.write(f"RC: {res.returncode}\\nSTDOUT:\\n{res.stdout}\\nSTDERR:\\n{res.stderr}")
            
        if res.returncode == 0 and res.stdout.strip():
            import csv, io
            reader = csv.reader(io.StringIO(res.stdout.strip()))
            rows = list(reader)
            if len(rows) > 1:
                headers = [h.strip().strip('"').lower() for h in rows[0]]
                data = rows[1]
                last_idx, next_idx = -1, -1
                for i, h in enumerate(headers):
                    if ("last" in h or "ltimo" in h or "ltima" in h or "último" in h) and ("tiempo" in h or "time" in h or "hora" in h or "run" in h or "ejecu" in h):
                        # Evitar que haga match con "Último resultado" (Last Result)
                        if "resultado" not in h and "result" not in h:
                            last_idx = i
                    if "next" in h or ("pr" in h and "xima" in h) or "próximo" in h or "próxima" in h or ("hora" in h and "ejecu" in h and "pr" in h):
                        next_idx = i
                
                # Fallbacks por si el encoding de Windows rompe las letras
                if last_idx == -1 and len(headers) > 5: last_idx = 5
                if next_idx == -1 and len(headers) > 2: next_idx = 2
                        
                if last_idx != -1 and next_idx != -1:
                    return {"last_run": data[last_idx].strip().strip('"'), "next_run": data[next_idx].strip().strip('"')}
    except Exception as e:
        logger.warning(f"No se pudo consultar la tarea remota: {e}")
    return None

