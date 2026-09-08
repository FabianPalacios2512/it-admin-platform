import os
import tempfile
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import paramiko
from datetime import datetime
import re

router = APIRouter(prefix="/pbx/recordings", tags=["PBX Recordings"])

# SSH credentials
SSH_HOST = "190.145.227.29"
SSH_USER = "root"
SSH_PASS = "P0w2rb00k2021*"
RECORDINGS_BASE_DIR = "/var/spool/asterisk/monitor"

# IPs de confianza de la empresa (Sucursales/Locales) que no deben ser bloqueadas ni marcadas como Brecha
TRUSTED_IPS = ["190.145.227.25", "190.145.227.29", "127.0.0.1"]

class BlockIPRequest(BaseModel):
    ip: str

class UnblockIPRequest(BaseModel):
    ip: str

class RecordingsResponse(BaseModel):
    status: str
    data: list
    message: Optional[str] = None

def _get_ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SSH_HOST, port=22, username=SSH_USER, password=SSH_PASS, timeout=10)
    return client

def remove_file(path: str):
    try:
        os.remove(path)
    except Exception:
        pass

@router.get("/list", response_model=RecordingsResponse)
def list_recordings(date: str, extension: Optional[str] = None):
    """
    Lista grabaciones para una fecha específica (YYYY-MM-DD).
    Opcional: filtrar por extensión.
    """
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        year = dt.strftime("%Y")
        month = dt.strftime("%m")
        day = dt.strftime("%d")
        target_dir = f"{RECORDINGS_BASE_DIR}/{year}/{month}/{day}"
        
        client = _get_ssh_client()
        
        # Use find to get wav files in the specific directory
        cmd = f"find {target_dir} -maxdepth 1 -name '*.wav' -printf '%f|%s\\n' 2>/dev/null"
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode('utf-8').strip()
        client.close()
        
        if not output:
            return {"status": "success", "data": []}
            
        recordings = []
        for line in output.split('\n'):
            if not line: continue
            parts = line.split('|')
            if len(parts) != 2: continue
            filename = parts[0]
            size_bytes = int(parts[1])
            
            # Formato típico: exten-61049-3105942055-20251212-084412-1765546993.571618.wav
            # o out-93012808438-3977-20251212-151752-...
            name_parts = filename.split('-')
            
            # Extraer info básica
            call_type = name_parts[0] if len(name_parts) > 0 else "unknown"
            src = ""
            dst = ""
            time_str = ""
            
            if len(name_parts) >= 5:
                src = name_parts[1]
                dst = name_parts[2]
                time_str = f"{name_parts[4][:2]}:{name_parts[4][2:4]}:{name_parts[4][4:6]}"
            
            # Filtrar por extensión si se provee
            if extension and (extension not in src and extension not in dst):
                continue
                
            recordings.append({
                "filename": filename,
                "filepath": f"{target_dir}/{filename}",
                "type": call_type,
                "source": src,
                "destination": dst,
                "time": time_str,
                "size_mb": round(size_bytes / (1024 * 1024), 2)
            })
            
        # Ordenar por hora descendente (más recientes primero)
        recordings.sort(key=lambda x: x["time"], reverse=True)
        
        return {"status": "success", "data": recordings}
        
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

@router.get("/play")
def play_recording(filepath: str, background_tasks: BackgroundTasks):
    """
    Descarga el archivo wav vía SFTP y lo retorna como un Stream para que el navegador lo reproduzca.
    """
    if not filepath.startswith(RECORDINGS_BASE_DIR):
        raise HTTPException(status_code=403, detail="Ruta no permitida")
        
    if not filepath.endswith(".wav"):
        raise HTTPException(status_code=400, detail="El archivo no es wav")
        
    try:
        client = _get_ssh_client()
        sftp = client.open_sftp()
        
        # Check if remote file exists
        try:
            sftp.stat(filepath)
        except FileNotFoundError:
            sftp.close()
            client.close()
            raise HTTPException(status_code=404, detail="Grabación no encontrada en el servidor")
            
        # Create temp file
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        # Download file
        sftp.get(filepath, temp_path)
        sftp.close()
        client.close()
        
        # Return file and schedule deletion
        background_tasks.add_task(remove_file, temp_path)
        
        return FileResponse(
            temp_path,
            media_type="audio/wav",
            filename=os.path.basename(filepath)
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Error descargando el archivo: {str(e)}")

@router.get("/security/auth-logs")
def get_auth_logs(limit: int = 100):
    """
    Extrae los últimos registros de autenticación SIP y SSH, ordenados cronológicamente.
    """
    try:
        client = _get_ssh_client()
        cmd_ast = f"grep -E 'Registered SIP|Wrong password' /var/log/asterisk/full | grep -v \"at 190.145.\" | grep -v \"for '190.145.\" | tail -n {limit}"
        cmd_ssh = f"grep -E 'Accepted password|Failed password' /var/log/secure | grep -v '190.145.' | tail -n {limit}"
        
        stdin, stdout, stderr = client.exec_command(cmd_ast)
        output_ast = stdout.read().decode('utf-8').strip()
        
        stdin, stdout, stderr = client.exec_command(cmd_ssh)
        output_ssh = stdout.read().decode('utf-8').strip()
        
        client.close()
        
        logs = []
        ip_failures = {} 
        current_year = datetime.now().year
        
        # Process Asterisk
        if output_ast:
            for line in output_ast.split('\n'):
                if not line: continue
                try:
                    time_part = line[line.find('[')+1 : line.find(']')]
                    try:
                        dt = datetime.strptime(time_part, '%Y-%m-%d %H:%M:%S')
                    except:
                        dt = datetime.min
                        
                    is_failed = "Wrong password" in line
                    ip = "Unknown"
                    ext = "Unknown"
                    
                    if is_failed:
                        ip_match = re.search(r"failed for '([0-9\.]+):", line)
                        if ip_match: ip = ip_match.group(1)
                        ext_match = re.search(r"<sip:([0-9]+)@", line)
                        if ext_match: ext = ext_match.group(1)
                        if ip != "Unknown":
                            ip_failures[ip] = ip_failures.get(ip, 0) + 1
                    else:
                        ip_match = re.search(r"at ([0-9\.]+):", line)
                        if ip_match: ip = ip_match.group(1)
                        ext_match = re.search(r"Registered SIP '([0-9]+)'", line)
                        if ext_match: ext = ext_match.group(1)
                        
                    is_breach = False
                    if not is_failed and ip_failures.get(ip, 0) > 5 and ip not in TRUSTED_IPS and not ip.startswith("192.168."):
                        is_breach = True
                    else:
                        if not is_failed: ip_failures[ip] = 0
                        
                    logs.append({
                        "timestamp": dt.strftime('%Y-%m-%d %H:%M:%S') if dt != datetime.min else time_part,
                        "ip": ip,
                        "extension": ext,
                        "status": "FALLA" if is_failed else "OK",
                        "is_breach": is_breach,
                        "attempts_count": ip_failures.get(ip, 0) if ip != "Unknown" else 0,
                        "raw": line,
                        "protocol": "SIP",
                        "dt": dt
                    })
                except Exception:
                    continue
                    
        # Process SSH
        if output_ssh:
            for line in output_ssh.split('\n'):
                if not line: continue
                try:
                    time_part = line[:15]
                    try:
                        # Sep  7 19:43:05
                        dt_ssh = datetime.strptime(time_part, '%b %d %H:%M:%S')
                        dt_ssh = dt_ssh.replace(year=current_year)
                    except:
                        dt_ssh = datetime.min
                        
                    is_failed = "Failed password" in line
                    ip = "Unknown"
                    ext = "Unknown"
                    
                    user_match = re.search(r"for (?:invalid user )?(\S+) from", line)
                    if user_match: ext = user_match.group(1)
                    
                    ip_match = re.search(r"from ([0-9\.]+)", line)
                    if ip_match: ip = ip_match.group(1)
                    
                    if is_failed and ip != "Unknown":
                        ip_failures[ip] = ip_failures.get(ip, 0) + 1
                        
                    is_breach = False
                    if not is_failed and ip_failures.get(ip, 0) > 5 and ip not in TRUSTED_IPS and not ip.startswith("192.168."):
                        is_breach = True
                    else:
                        if not is_failed: ip_failures[ip] = 0
                        
                    logs.append({
                        "timestamp": dt_ssh.strftime('%Y-%m-%d %H:%M:%S') if dt_ssh != datetime.min else time_part,
                        "ip": ip,
                        "extension": ext,
                        "status": "FALLA" if is_failed else "OK",
                        "is_breach": is_breach,
                        "attempts_count": ip_failures.get(ip, 0) if ip != "Unknown" else 0,
                        "raw": line,
                        "protocol": "SSH",
                        "dt": dt_ssh
                    })
                except Exception:
                    continue

        # Sort combined logs by datetime descending
        logs.sort(key=lambda x: x["dt"], reverse=True)
        for log in logs:
            del log["dt"]
            
        return {"status": "success", "data": logs[:limit]}
        
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

@router.post("/security/block-ip")
def block_ip(request: BlockIPRequest):
    """
    Bloquea una IP permanentemente usando firewalld en el PBX.
    """
    try:
        # Basic validation to prevent command injection
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", request.ip):
            raise HTTPException(status_code=400, detail="Formato de IP inválido")
            
        client = _get_ssh_client()
        # Evitar bloquear IPs locales
        if request.ip in TRUSTED_IPS or request.ip.startswith("192.168."):
            client.close()
            raise HTTPException(status_code=403, detail="No puedes bloquear una IP de confianza de la empresa.")
            
        # Drop traffic from this IP unconditionally using firewalld rich rule
        cmd = f"firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"{request.ip}\" drop'"
        stdin, stdout, stderr = client.exec_command(cmd)
        
        # Reload firewalld to apply
        client.exec_command("firewall-cmd --reload")
        
        # Also drop in raw table immediately to kill active UDP attacks (bypassing conntrack)
        client.exec_command(f"iptables -I INPUT 1 -s {request.ip} -j DROP")
        client.exec_command(f"iptables -t raw -I PREROUTING 1 -s {request.ip} -j DROP")
        
        client.close()
        
        return {"status": "success", "message": f"IP {request.ip} bloqueada exitosamente en el firewall del PBX."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/security/blocked-ips")
def get_blocked_ips():
    """
    Obtiene la lista de IPs bloqueadas en Firewalld y Fail2Ban con sus motivos y fecha de bloqueo.
    """
    try:
        client = _get_ssh_client()
        blocked_list = []
        
        # Pre-fetch fail2ban timestamps to avoid running a command per IP
        cmd_f2b_logs = "grep 'Ban ' /var/log/fail2ban.log | awk '{print $1\" \"$2\" \"$NF}'"
        stdin, stdout, stderr = client.exec_command(cmd_f2b_logs)
        f2b_logs_output = stdout.read().decode('utf-8').strip()
        
        ban_times = {}
        if f2b_logs_output:
            for line in f2b_logs_output.split('\n'):
                parts = line.split()
                if len(parts) >= 3:
                    ip = parts[-1]
                    ts = f"{parts[0]} {parts[1].split(',')[0]}"
                    ban_times[ip] = ts
        
        # 1. Firewalld Rich Rules
        cmd_fw = "firewall-cmd --list-rich-rules 2>/dev/null | grep drop"
        stdin, stdout, stderr = client.exec_command(cmd_fw)
        output_fw = stdout.read().decode('utf-8').strip()
        if output_fw:
            for line in output_fw.split('\n'):
                match = re.search(r'source address="([^"]+)"', line)
                if match:
                    blocked_list.append({
                        "ip": match.group(1),
                        "source": "FIREWALLD",
                        "reason": "Bloqueo Manual Administrativo",
                        "timestamp": "N/A (Regla Manual)"
                    })
                    
        # 2. Fail2Ban SSH
        cmd_f2b_ssh = "fail2ban-client status sshd 2>/dev/null | grep 'Banned IP list'"
        stdin, stdout, stderr = client.exec_command(cmd_f2b_ssh)
        output_f2b_ssh = stdout.read().decode('utf-8').strip()
        if output_f2b_ssh:
            parts = output_f2b_ssh.split(':')
            if len(parts) > 1:
                ips = parts[1].strip().split()
                for ip in ips:
                    blocked_list.append({
                        "ip": ip,
                        "source": "FAIL2BAN",
                        "reason": "Fuerza Bruta SSH",
                        "timestamp": ban_times.get(ip, "Desconocida")
                    })

        # 3. Fail2Ban Asterisk
        cmd_f2b_ast = "fail2ban-client status asterisk 2>/dev/null | grep 'Banned IP list'"
        stdin, stdout, stderr = client.exec_command(cmd_f2b_ast)
        output_f2b_ast = stdout.read().decode('utf-8').strip()
        if output_f2b_ast:
            parts = output_f2b_ast.split(':')
            if len(parts) > 1:
                ips = parts[1].strip().split()
                for ip in ips:
                    blocked_list.append({
                        "ip": ip,
                        "source": "FAIL2BAN",
                        "reason": "Ataque SIP/PBX",
                        "timestamp": ban_times.get(ip, "Desconocida")
                    })

        # Sort by most recent ban if possible (using timestamp string sort, fail2ban format is YYYY-MM-DD HH:MM:SS)
        blocked_list.sort(key=lambda x: x['timestamp'], reverse=True)

        client.close()
        return {"status": "success", "data": blocked_list}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

@router.post("/security/unblock-ip")
def unblock_ip(request: UnblockIPRequest):
    """
    Desbloquea una IP permanentemente usando firewalld en el PBX.
    """
    try:
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", request.ip):
            raise HTTPException(status_code=400, detail="Formato de IP inválido")
            
        client = _get_ssh_client()
        # Remove from firewalld
        cmd = f"firewall-cmd --permanent --remove-rich-rule='rule family=\"ipv4\" source address=\"{request.ip}\" drop'"
        client.exec_command(cmd)
        
        # Reload firewalld
        client.exec_command("firewall-cmd --reload")
        
        # Also clean up memory rules if they exist
        client.exec_command(f"while iptables -D INPUT -s {request.ip} -j DROP 2>/dev/null; do :; done")
        client.exec_command(f"while iptables -t raw -D PREROUTING -s {request.ip} -j DROP 2>/dev/null; do :; done")
        
        # Unban from fail2ban
        client.exec_command(f"fail2ban-client set sshd unbanip {request.ip} 2>/dev/null")
        client.exec_command(f"fail2ban-client set asterisk unbanip {request.ip} 2>/dev/null")
        
        client.close()
        
        return {"status": "success", "message": f"IP {request.ip} desbloqueada exitosamente."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/security/scan")
def run_vulnerability_scan():
    """
    Escanea la configuración y los logs para detectar contraseñas débiles y extensiones comprometidas.
    """
    try:
        client = _get_ssh_client()
        
        # 1. Auditoría de Contraseñas (sip_additional.conf)
        cmd_secrets = "grep -E '^\\[|^secret=' /etc/asterisk/sip_additional.conf"
        stdin, stdout, stderr = client.exec_command(cmd_secrets)
        secrets_raw = stdout.read().decode('utf-8').splitlines()
        
        extensions = {}
        current_ext = None
        for line in secrets_raw:
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                current_ext = line[1:-1]
            elif line.startswith('secret=') and current_ext:
                pwd = line.split('=', 1)[1]
                if current_ext.isdigit():
                    extensions[current_ext] = pwd
                
        pwd_counts = {}
        for ext, pwd in extensions.items():
            if pwd not in pwd_counts:
                pwd_counts[pwd] = []
            pwd_counts[pwd].append(ext)
            
        weak_passwords = []
        for pwd, exts in pwd_counts.items():
            if len(exts) > 1 or len(pwd) < 8 or "Hogar2023" in pwd or pwd.isdigit():
                weak_passwords.append({
                    "password_mask": pwd[:2] + "****" + pwd[-2:] if len(pwd) >= 4 else "****",
                    "extensions": exts,
                    "reason": "Clave compartida por varias extensiones" if len(exts) > 1 else "Clave muy débil o por defecto"
                })
                
        # 2. Análisis de Fuerza Bruta y Compromiso (Lógica de >5 fallos -> OK)
        # Obtenemos los eventos de los últimos 2 logs para que sea rápido y no colapse SSH
        cmd_logs = "cat /var/log/asterisk/full.1 /var/log/asterisk/full 2>/dev/null | grep -E 'Wrong password|Registered SIP' | tail -n 15000"
        stdin, stdout, stderr = client.exec_command(cmd_logs)
        logs_raw = stdout.read().decode('utf-8', errors='ignore').splitlines()
        client.close()
        
        ext_failures = {}
        compromised_exts = {}
        
        for line in logs_raw:
            # Parse failures
            if "Wrong password" in line:
                match = re.search(r"<sip:(\d+)@", line)
                if match:
                    ext = match.group(1)
                    ext_failures[ext] = ext_failures.get(ext, 0) + 1
            
            # Parse successes
            elif "Registered SIP" in line:
                match = re.search(r"Registered SIP '(\d+)' at ([0-9\.]+)", line)
                if match:
                    # Lógica Anti-Falsos Positivos con GeoIP:
                    # Usamos un request rápido a ip-api para ver de qué país es la IP
                    import requests
                    is_colombia = False
                    if ip not in TRUSTED_IPS and not ip.startswith("192.") and not ip.startswith("10.") and not ip.startswith("172."):
                        try:
                            # Timeout corto para no colgar el script
                            geo_resp = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=2)
                            if geo_resp.status_code == 200:
                                if geo_resp.json().get("countryCode") == "CO":
                                    is_colombia = True
                        except Exception:
                            pass # Si falla el API, asumimos lo peor o seguimos
                    else:
                        is_colombia = True # IPs locales o de confianza se asumen seguras

                    # Condición de Alerta:
                    # 1. Si NO es de Colombia, se alerta de inmediato al primer intento (ataque externo directo).
                    # 2. Si SÍ es de Colombia (ej. trabajador remoto de Claro/Tigo), SOLO se alerta si intentó fuerza bruta (>5 fallos).
                    if not is_colombia or (is_colombia and ext_failures.get(ext, 0) > 5):
                        compromised_exts[ext] = {
                            "extension": ext,
                            "attacker_ip": ip,
                            "failed_attempts_before_success": ext_failures.get(ext, 0)
                        }
                    else:
                        # Registro exitoso sin tantos fallos = reset (para no acumular los fallos legítimos)
                        ext_failures[ext] = 0
                        
        # Preparar listas finales
        compromised_list = list(compromised_exts.values())
        
        # Extensions under attack (high failures, no success yet)
        under_attack_list = []
        for ext, count in ext_failures.items():
            if count > 20 and ext not in compromised_exts:
                under_attack_list.append({
                    "extension": ext,
                    "failed_attempts": count
                })
        
        # Ordenar under_attack de mayor a menor
        under_attack_list.sort(key=lambda x: x["failed_attempts"], reverse=True)
        
        return {
            "status": "success", 
            "data": {
                "compromised": compromised_list,
                "under_attack": under_attack_list[:20],
                "weak_passwords": weak_passwords
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}

@router.get("/security/status")
def get_security_status():
    """
    Obtiene el estado de los servicios de seguridad del PBX (firewalld, fail2ban)
    junto con KPIs en tiempo real: intentos fallidos 24h, IPs bloqueadas, IPs sospechosas.
    """
    try:
        client = _get_ssh_client()
        status_data = {}

        # --- Estado de servicios ---
        for svc in ['firewalld', 'iptables', 'httpd']:
            stdin, stdout, stderr = client.exec_command(f"systemctl is-active {svc}")
            status_data[svc] = stdout.read().decode('utf-8').strip() == "active"
            
        stdin, stdout, stderr = client.exec_command("uptime -p")
        status_data["uptime"] = stdout.read().decode('utf-8').strip().replace("up ", "")

        stdin, stdout, stderr = client.exec_command("systemctl is-active fail2ban")
        status_data["fail2ban"] = stdout.read().decode('utf-8').strip() == "active"

        # --- KPI 1: Intentos fallidos hoy (SSH + Asterisk) ---
        cmd_ssh_fails = "grep \"$(LC_ALL=C date '+%b %e')\" /var/log/secure 2>/dev/null | grep 'Failed password' | wc -l"
        stdin, stdout, stderr = client.exec_command(cmd_ssh_fails)
        ssh_fails = int(stdout.read().decode('utf-8').strip() or 0)

        cmd_ast_fails = "grep \"$(date '+%Y-%m-%d')\" /var/log/asterisk/full 2>/dev/null | grep -E 'Wrong password|failed to authenticate|failed for' | wc -l"
        stdin, stdout, stderr = client.exec_command(cmd_ast_fails)
        ast_fails = int(stdout.read().decode('utf-8').strip() or 0)
        
        status_data["failed_attempts_24h"] = ssh_fails + ast_fails

        # --- KPI 2: IPs actualmente bloqueadas (Fail2Ban + Firewalld Rich Rules) ---
        cmd_f2b_banned = (
            "fail2ban-client status | grep 'Jail list:' | sed -E 's/^[^:]+:[ \\t]+//' | sed 's/,//g' | "
            "xargs -n1 fail2ban-client status | grep 'Currently banned:' | awk '{sum+=$4} END {print sum}'"
        )
        stdin, stdout, stderr = client.exec_command(cmd_f2b_banned)
        try:
            f2b_blocked = int(stdout.read().decode('utf-8').strip() or 0)
        except Exception:
            f2b_blocked = 0

        cmd_firewalld_banned = "firewall-cmd --list-rich-rules 2>/dev/null | grep 'drop' | wc -l"
        stdin, stdout, stderr = client.exec_command(cmd_firewalld_banned)
        try:
            firewalld_blocked = int(stdout.read().decode('utf-8').strip() or 0)
        except Exception:
            firewalld_blocked = 0

        status_data["blocked_ips"] = f2b_blocked + firewalld_blocked

        # --- KPI 3: IPs sospechosas (>= 5 intentos fallidos hoy en SSH) ---
        cmd_suspicious = (
            "grep \"$(LC_ALL=C date '+%b %e')\" /var/log/secure 2>/dev/null | grep 'Failed password' "
            "| grep -oP '[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+' "
            "| sort | uniq -c | awk '$1 >= 5 {print $2}' | wc -l"
        )
        stdin, stdout, stderr = client.exec_command(cmd_suspicious)
        try:
            status_data["suspicious_ips"] = int(stdout.read().decode('utf-8').strip() or 0)
        except Exception:
            status_data["suspicious_ips"] = 0

        client.close()

        # Estado general: sin anomalías si fail2ban activo y sin intentos recientes significativos
        status_data["anomaly"] = (
            not status_data["fail2ban"]
            or status_data["failed_attempts_24h"] > 50
            or status_data["suspicious_ips"] > 5
        )

        return {"status": "success", "data": status_data}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}



@router.get("/security/whitelist")
def get_security_whitelist():
    try:
        client = _get_ssh_client()
        stdin, stdout, stderr = client.exec_command("grep -m 1 '^ignoreip =' /etc/fail2ban/jail.local | cut -d'=' -f2")
        output = stdout.read().decode('utf-8').strip()
        client.close()
        
        ips = [ip.strip() for ip in output.split() if ip.strip()]
        return {"status": "success", "data": ips}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}

@router.post("/security/whitelist")
def add_security_whitelist(payload: dict):
    try:
        ip = payload.get("ip")
        if not ip:
            return {"status": "error", "message": "IP is required"}
            
        client = _get_ssh_client()
        # Check if IP already exists
        stdin, stdout, stderr = client.exec_command("grep -m 1 '^ignoreip =' /etc/fail2ban/jail.local")
        current_ignoreip = stdout.read().decode('utf-8').strip()
        
        if ip in current_ignoreip:
            client.close()
            return {"status": "success", "message": "IP already in whitelist"}
            
        # Append IP safely
        stdin, stdout, stderr = client.exec_command(f"sed -i 's|^ignoreip = .*|& {ip}|' /etc/fail2ban/jail.local")
        stderr_output = stderr.read().decode('utf-8').strip()
        if stderr_output:
            raise Exception(stderr_output)
            
        # Restart Fail2Ban to apply changes
        stdin, stdout, stderr = client.exec_command("systemctl restart fail2ban")
        stderr_output = stderr.read().decode('utf-8').strip()
        if stderr_output:
            raise Exception(f"Fail2Ban Restart Error: {stderr_output}")
            
        client.close()
        return {"status": "success", "message": "IP added and Fail2Ban restarted"}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
