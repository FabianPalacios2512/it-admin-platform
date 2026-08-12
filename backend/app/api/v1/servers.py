"""
Endpoints de configuración de servidores v2.0.
Soporte multi-OS: Windows (WMI) y Linux (SSH via paramiko).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.database import SessionLocal
from app.models.server import ServerConfig
from app.core.encryption import encrypt_password, decrypt_password

router = APIRouter()


# ══════════════════════════════════════════════════════════════
# ESQUEMAS v2.0
# ══════════════════════════════════════════════════════════════
class ServerCreateRequest(BaseModel):
    name: str
    server_type: str        # "da", "ha", "files", "printers", "app", "rds"
    ip: str
    domain: Optional[str] = ""
    admin_user: str
    admin_pass: str
    allowed_groups: Optional[str] = ""
    is_primary: bool = False
    # ── v2.0: Multi-OS ──────────────────────────────────────────
    os_type: Optional[str] = "windows"   # "windows" | "linux"
    ssh_user: Optional[str] = ""         # Usuario SSH (Linux)
    ssh_key: Optional[str] = ""          # Llave privada PEM (opcional, Linux)
    ssh_port: Optional[int] = 22         # Puerto SSH


class ServerUpdateRequest(BaseModel):
    name: Optional[str] = None
    server_type: Optional[str] = None
    ip: Optional[str] = None
    domain: Optional[str] = None
    admin_user: Optional[str] = None
    admin_pass: Optional[str] = None   # Si viene vacío, no se cambia
    allowed_groups: Optional[str] = None
    is_primary: Optional[bool] = None
    # ── v2.0: Multi-OS ──────────────────────────────────────────
    os_type: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_key: Optional[str] = None
    ssh_port: Optional[int] = None


# ══════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════
SERVER_TYPES = {
    "da": "Directorio Activo",
    "ha": "Alta Disponibilidad (HA)",
    "files": "Servidor de Archivos",
    "printers": "Servidor de Impresoras",
    "app": "Servidor de Aplicaciones",
    "rds": "Servidor RDS / Escritorio Remoto",
}


# ══════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/")
def list_servers():
    """Lista todos los servidores configurados (sin contraseñas)."""
    db = SessionLocal()
    servers = db.query(ServerConfig).order_by(ServerConfig.created_at).all()
    result = []
    for s in servers:
        result.append({
            "id": s.id,
            "name": s.name,
            "server_type": s.server_type,
            "server_type_label": SERVER_TYPES.get(s.server_type, s.server_type),
            "ip": s.ip,
            "domain": s.domain or "",
            "admin_user": s.admin_user,
            "allowed_groups": s.allowed_groups or "",
            "is_primary": s.is_primary,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            # v2.0
            "os_type": getattr(s, "os_type", "windows") or "windows",
            "ssh_user": getattr(s, "ssh_user", "") or "",
            "ssh_port": getattr(s, "ssh_port", 22) or 22,
        })
    db.close()
    return result


@router.post("/")
def create_server(req: ServerCreateRequest):
    """Crea un nuevo servidor (Windows o Linux)."""
    db = SessionLocal()
    try:
        if req.is_primary:
            db.query(ServerConfig).filter(
                ServerConfig.server_type == req.server_type,
                ServerConfig.is_primary == True
            ).update({"is_primary": False})

        # Encriptar llave SSH si se provee
        ssh_key_encrypted = None
        if req.os_type == "linux" and req.ssh_key and req.ssh_key.strip():
            ssh_key_encrypted = encrypt_password(req.ssh_key.strip())

        server = ServerConfig(
            name=req.name,
            server_type=req.server_type,
            ip=req.ip,
            domain=req.domain or "",
            admin_user=req.admin_user,
            admin_pass=encrypt_password(req.admin_pass),
            allowed_groups=req.allowed_groups or "",
            is_primary=req.is_primary,
            # v2.0
            os_type=req.os_type or "windows",
            ssh_user=req.ssh_user or "",
            ssh_key=ssh_key_encrypted,
            ssh_port=req.ssh_port or 22,
        )
        db.add(server)
        db.commit()
        db.refresh(server)
        return {"success": True, "id": server.id, "message": f"Servidor '{req.name}' creado correctamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/{server_id}")
def update_server(server_id: int, req: ServerUpdateRequest):
    """Actualiza un servidor existente."""
    db = SessionLocal()
    try:
        server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Servidor no encontrado.")

        if req.name is not None:
            server.name = req.name
        if req.server_type is not None:
            server.server_type = req.server_type
        if req.ip is not None:
            server.ip = req.ip
        if req.domain is not None:
            server.domain = req.domain
        if req.admin_user is not None:
            server.admin_user = req.admin_user
        if req.admin_pass and req.admin_pass.strip():
            server.admin_pass = encrypt_password(req.admin_pass)
        if req.allowed_groups is not None:
            server.allowed_groups = req.allowed_groups
        if req.is_primary is not None:
            if req.is_primary:
                db.query(ServerConfig).filter(
                    ServerConfig.server_type == server.server_type,
                    ServerConfig.id != server_id,
                    ServerConfig.is_primary == True
                ).update({"is_primary": False})
            server.is_primary = req.is_primary
        # v2.0
        if req.os_type is not None:
            server.os_type = req.os_type
        if req.ssh_user is not None:
            server.ssh_user = req.ssh_user
        if req.ssh_port is not None:
            server.ssh_port = req.ssh_port
        if req.ssh_key is not None and req.ssh_key.strip():
            server.ssh_key = encrypt_password(req.ssh_key.strip())

        db.commit()
        return {"success": True, "message": f"Servidor '{server.name}' actualizado."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/{server_id}")
def delete_server(server_id: int):
    """Elimina un servidor."""
    db = SessionLocal()
    try:
        server = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Servidor no encontrado.")
        name = server.name
        db.delete(server)
        db.commit()
        return {"success": True, "message": f"Servidor '{name}' eliminado."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/{server_id}/test")
def test_server_connection(server_id: int):
    """Prueba la conexión a un servidor guardado (LDAP / WMI / SSH)."""
    db = SessionLocal()
    try:
        server_cfg = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
        if not server_cfg:
            raise HTTPException(status_code=404, detail="Servidor no encontrado.")

        os_type = getattr(server_cfg, "os_type", "windows") or "windows"

        if os_type == "linux":
            return _test_ssh_connection(
                ip=server_cfg.ip,
                port=getattr(server_cfg, "ssh_port", 22) or 22,
                username=server_cfg.ssh_user or server_cfg.admin_user,
                password=decrypt_password(server_cfg.admin_pass),
                ssh_key_encrypted=getattr(server_cfg, "ssh_key", None),
            )

        password = decrypt_password(server_cfg.admin_pass)
        if server_cfg.server_type in ["da", "ha"]:
            from ldap3 import Server, Connection, ALL
            server = Server(server_cfg.ip, get_info=ALL)
            conn = Connection(server, user=server_cfg.admin_user, password=password, auto_bind=True)
            info = conn.server.info
            conn.unbind()
            server_name = str(info.other.get('dnsHostName', [''])[0]) if info and info.other else server_cfg.ip
            return {"success": True, "message": f"Conexión LDAP exitosa a {server_cfg.ip}", "server_name": server_name}
        else:
            import wmi, pythoncom
            pythoncom.CoInitialize()
            try:
                c = wmi.WMI(computer=server_cfg.ip, user=server_cfg.admin_user, password=password)
            except Exception as e:
                if "local connections" in str(e):
                    c = wmi.WMI()
                else:
                    raise
            os_info = c.Win32_OperatingSystem()[0]
            return {"success": True, "message": f"Conexión WMI exitosa a {os_info.CSName}"}
            
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "message": f"Error de conexión: {str(e)}"}
    finally:
        db.close()


@router.post("/test-new")
def test_new_connection(req: ServerCreateRequest):
    """Prueba la conexión a un servidor ANTES de guardarlo."""
    try:
        os_type = req.os_type or "windows"

        if os_type == "linux":
            return _test_ssh_connection(
                ip=req.ip,
                port=req.ssh_port or 22,
                username=req.ssh_user or req.admin_user,
                password=req.admin_pass,
                ssh_key_encrypted=None,  # Llave en texto plano (aún no guardada)
                ssh_key_plain=req.ssh_key if req.ssh_key and req.ssh_key.strip() else None,
            )

        if req.server_type in ["da", "ha"]:
            from ldap3 import Server, Connection, ALL
            server = Server(req.ip, get_info=ALL)
            conn = Connection(server, user=req.admin_user, password=req.admin_pass, auto_bind=True)
            conn.unbind()
            return {"success": True, "message": f"Conexión LDAP exitosa a {req.ip}"}
        else:
            import wmi, pythoncom
            pythoncom.CoInitialize()
            try:
                c = wmi.WMI(computer=req.ip, user=req.admin_user, password=req.admin_pass)
            except Exception as e:
                if "local connections" in str(e):
                    c = wmi.WMI()
                else:
                    raise
            os_info = c.Win32_OperatingSystem()[0]
            return {"success": True, "message": f"Conexión WMI exitosa a {os_info.CSName}"}
    except Exception as e:
        return {"success": False, "message": f"Error de conexión: {str(e)}"}


@router.post("/generate-ssh-key")
def generate_ssh_key():
    """Genera un par de llaves SSH (RSA) dinámicamente."""
    try:
        import paramiko
        import io
        key = paramiko.RSAKey.generate(bits=2048)
        out = io.StringIO()
        key.write_private_key(out)
        private_key_str = out.getvalue()
        public_key_str = f"{key.get_name()} {key.get_base64()} it-admin-platform"
        return {"success": True, "private_key": private_key_str, "public_key": public_key_str}
    except Exception as e:
        return {"success": False, "message": f"Error generando llave: {str(e)}"}


# ══════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════

def _load_private_key(key_str: str):
    import io
    import paramiko
    key_str = key_str.strip()
    if key_str.startswith("ssh-rsa ") or key_str.startswith("ssh-ed25519 ") or key_str.startswith("ecdsa-sha2-nistp256 "):
        raise ValueError("Parece que ingresaste una llave PÚBLICA (ssh-ed25519 / ssh-rsa). Debes ingresar tu llave PRIVADA (empieza con -----BEGIN...).")
    
    for cls in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]:
        try:
            return cls.from_private_key(io.StringIO(key_str))
        except paramiko.ssh_exception.SSHException:
            pass
    raise ValueError("not a valid private key file o formato no soportado")

def _test_ssh_connection(
    ip: str,
    port: int,
    username: str,
    password: str,
    ssh_key_encrypted: Optional[str] = None,
    ssh_key_plain: Optional[str] = None,
) -> dict:
    """Prueba conexión SSH y ejecuta 'hostname' para validar credenciales."""
    import io
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {
        "hostname": ip,
        "port": port,
        "username": username,
        "timeout": 10,
        "banner_timeout": 10,
        "auth_timeout": 10,
        "allow_agent": False,
        "look_for_keys": False,
    }

    if ssh_key_encrypted:
        decrypted = decrypt_password(ssh_key_encrypted)
        connect_kwargs["pkey"] = _load_private_key(decrypted)
    elif ssh_key_plain:
        connect_kwargs["pkey"] = _load_private_key(ssh_key_plain)
    elif password:
        connect_kwargs["password"] = password

    try:
        client.connect(**connect_kwargs)
        stdin, stdout, stderr = client.exec_command("hostname", timeout=5)
        hostname = stdout.read().decode("utf-8", errors="replace").strip()
        client.close()
        return {"success": True, "message": f"Conexión SSH exitosa — hostname: {hostname or ip}"}
    except paramiko.AuthenticationException:
        return {"success": False, "message": "Autenticación SSH fallida. Verifica usuario y contraseña/llave."}
    except paramiko.ssh_exception.NoValidConnectionsError:
        return {"success": False, "message": f"No se pudo conectar a {ip}:{port}. ¿El servidor está activo?"}
    except Exception as e:
        return {"success": False, "message": f"Error SSH: {str(e)[:150]}"}
    finally:
        client.close()
