"""
linux_monitoring_service.py — Módulo SSH para métricas de servidores Linux
===========================================================================
Conecta via SSH (paramiko), ejecuta comandos nativos y retorna el MISMO
esquema JSON que el servicio Windows (monitoring_service.py), garantizando
compatibilidad total con el frontend.

Esquema de salida unificado:
{
    "status":      "online",
    "CPU":         34.5,
    "RAM_Total":   7.8,      # GB
    "RAM_Used":    3.2,      # GB
    "RAM_Percent": 41.0,
    "Disks": [
        {"DeviceID": "/",       "SizeGB": 50.0, "FreeGB": 22.5},
        {"DeviceID": "/data",   "SizeGB": 200.0, "FreeGB": 100.0}
    ],
    "UptimeDays":  12,
    "UptimeHours": 3
}
"""

import io
import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Timeout global SSH (segundos) ────────────────────────────────────────────
SSH_TIMEOUT = 10


def _get_ssh_client(server):
    """
    Crea y devuelve un cliente SSH autenticado para el servidor dado.
    Soporta autenticación por contraseña y por llave privada (PEM).
    """
    import paramiko
    from app.core.encryption import decrypt_password

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ip = server.ip
    port = server.ssh_port or 22
    username = server.ssh_user or server.admin_user
    password = decrypt_password(server.admin_pass) if server.admin_pass else None
    ssh_key_pem = server.ssh_key  # PEM encriptado (o None)

    connect_kwargs = {
        "hostname": ip,
        "port": port,
        "username": username,
        "timeout": SSH_TIMEOUT,
        "banner_timeout": SSH_TIMEOUT,
        "auth_timeout": SSH_TIMEOUT,
        "allow_agent": False,
        "look_for_keys": False,
    }

    if ssh_key_pem:
        decrypted_key = decrypt_password(ssh_key_pem) if ssh_key_pem else None
        if decrypted_key:
            key_str = decrypted_key.strip()
            for cls in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]:
                try:
                    connect_kwargs["pkey"] = cls.from_private_key(io.StringIO(key_str))
                    break
                except paramiko.ssh_exception.SSHException:
                    pass
    elif password:
        connect_kwargs["password"] = password

    client.connect(**connect_kwargs)
    return client


def _exec(client, cmd: str) -> str:
    """Ejecuta un comando remoto y retorna stdout como string. Lanza en caso de error."""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=SSH_TIMEOUT)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    return out


def get_linux_stats(server) -> dict:
    """
    Obtiene métricas de CPU, RAM, Disco y Uptime via SSH.
    Retorna el mismo esquema JSON que el servicio Windows.
    Nunca lanza excepción — retorna {"status": "error/offline/timeout", "error": "..."}.
    """
    try:
        return _get_linux_stats_internal(server)
    except Exception as e:
        err_msg = str(e)
        # Clasificar el tipo de error para el frontend
        if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
            return {"status": "timeout", "error": f"Timeout SSH ({SSH_TIMEOUT}s)"}
        if "authentication" in err_msg.lower() or "auth" in err_msg.lower():
            return {"status": "error", "error": "Autenticación SSH fallida"}
        if "connection refused" in err_msg.lower() or "no route" in err_msg.lower():
            return {"status": "offline", "error": f"Conexión rechazada: {server.ip}"}
        return {"status": "error", "error": err_msg[:200]}


def _get_linux_stats_internal(server) -> dict:
    import paramiko

    client = _get_ssh_client(server)
    try:
        # ── CPU (%) ─────────────────────────────────────────────────────────
        # top en modo batch, 1 ciclo → grep al CPU idle → resta a 100
        cpu_out = _exec(
            client,
            "top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}' 2>/dev/null || "
            "grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {printf \"%.1f\", usage}'"
        )
        try:
            cpu = round(float(cpu_out.replace(",", ".")), 1)
        except ValueError:
            cpu = 0.0

        # ── RAM ─────────────────────────────────────────────────────────────
        # free -m → línea "Mem:" → campos: total used free shared buff/cache available
        ram_out = _exec(client, "free -m | awk '/^Mem:/{print $2, $3}'")
        ram_total_mb, ram_used_mb = 0, 0
        try:
            parts = ram_out.split()
            ram_total_mb = int(parts[0])
            ram_used_mb = int(parts[1])
        except (ValueError, IndexError):
            pass

        ram_total_gb = round(ram_total_mb / 1024, 2)
        ram_used_gb = round(ram_used_mb / 1024, 2)
        ram_percent = round((ram_used_mb / ram_total_mb) * 100, 1) if ram_total_mb > 0 else 0.0

        # ── DISCO ────────────────────────────────────────────────────────────
        # df -h → todas las particiones reales (excluye tmpfs, devtmpfs, etc.)
        # Retorna múltiples filas en formato: mountpoint size_gb free_gb
        disk_out = _exec(
            client,
            "df --output=target,size,avail -BG 2>/dev/null | "
            "awk 'NR>1 && $1!~/tmpfs|devtmpfs|udev|overlay|shm/ {gsub(/G/,\"\",$2); gsub(/G/,\"\",$3); print $1, $2, $3}'"
        )
        disks = []
        for line in disk_out.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                try:
                    size_gb = float(parts[1])
                    free_gb = float(parts[2])
                    disks.append({
                        "DeviceID": parts[0],    # ej: "/" o "/data"
                        "SizeGB": size_gb,
                        "FreeGB": free_gb
                    })
                except ValueError:
                    continue

        # Fallback: si el comando df --output no funciona (sistemas más viejos)
        if not disks:
            disk_out2 = _exec(client, "df -BG | awk 'NR>1 && $1~/^\\/dev/{print $6, $2, $4}'")
            for line in disk_out2.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        size_gb = float(parts[1].replace("G", ""))
                        free_gb = float(parts[2].replace("G", ""))
                        disks.append({"DeviceID": parts[0], "SizeGB": size_gb, "FreeGB": free_gb})
                    except ValueError:
                        continue

        # ── UPTIME ───────────────────────────────────────────────────────────
        # /proc/uptime → segundos en línea
        uptime_out = _exec(client, "cat /proc/uptime | awk '{print int($1)}'")
        try:
            total_seconds = int(uptime_out)
            uptime_days = total_seconds // 86400
            uptime_hours = (total_seconds % 86400) // 3600
        except ValueError:
            uptime_days, uptime_hours = 0, 0

        return {
            "status": "online",
            "CPU": cpu,
            "RAM_Total": ram_total_gb,
            "RAM_Used": ram_used_gb,
            "RAM_Percent": ram_percent,
            "Disks": disks,
            "UptimeDays": uptime_days,
            "UptimeHours": uptime_hours,
        }

    finally:
        client.close()


def get_linux_top_processes(server) -> list:
    """
    Obtiene el Top 5 de procesos que más CPU consumen en el servidor Linux.

    Retorna lista de dicts:
    [{"pid": 1234, "name": "python3", "cpu_percent": 45.2, "mem_percent": 3.1}, ...]
    Nunca lanza excepción — retorna lista vacía en caso de error.
    """
    try:
        client = _get_ssh_client(server)
        try:
            # ps -eo pid,comm,%cpu,%mem → sort por %cpu desc → top 5 (saltar header)
            out = _exec(
                client,
                "ps -eo pid,comm,%cpu,%mem --sort=-%cpu 2>/dev/null | head -n 6 | tail -n 5"
            )
            processes = []
            for line in out.splitlines():
                parts = line.split(None, 3)  # máximo 4 partes
                if len(parts) >= 4:
                    try:
                        processes.append({
                            "pid": int(parts[0]),
                            "name": parts[1][:30],               # truncar nombre largo
                            "cpu_percent": float(parts[2].replace(",", ".")),
                            "mem_percent": float(parts[3].replace(",", "."))
                        })
                    except ValueError:
                        continue
            return processes[:5]
        finally:
            client.close()
    except Exception as e:
        logger.warning(f"[Linux Processes] Error en {server.ip}: {e}")
        return []
