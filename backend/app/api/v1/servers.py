"""
Endpoints de configuración de servidores.
Permite agregar, editar, eliminar y probar conexión a servidores.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.database import SessionLocal
from app.models.server import ServerConfig
from app.core.encryption import encrypt_password, decrypt_password

router = APIRouter()


# ══════════════════════════════════════════════════════════════
# ESQUEMAS
# ══════════════════════════════════════════════════════════════
class ServerCreateRequest(BaseModel):
    name: str
    server_type: str        # "da", "ha", "files", "printers"
    ip: str
    domain: Optional[str] = ""
    admin_user: str
    admin_pass: str
    allowed_groups: Optional[str] = ""
    is_primary: bool = False


class ServerUpdateRequest(BaseModel):
    name: Optional[str] = None
    server_type: Optional[str] = None
    ip: Optional[str] = None
    domain: Optional[str] = None
    admin_user: Optional[str] = None
    admin_pass: Optional[str] = None   # Si viene vacío, no se cambia
    allowed_groups: Optional[str] = None
    is_primary: Optional[bool] = None


# ══════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════

SERVER_TYPES = {
    "da": "Directorio Activo",
    "ha": "Alta Disponibilidad (HA)",
    "files": "Servidor de Archivos",
    "printers": "Servidor de Impresoras",
    "app": "Servidor de Aplicaciones",
    "rds": "Servidor RDS / Escritorio Remoto",
}


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
        })
    db.close()
    return result


@router.post("/")
def create_server(req: ServerCreateRequest):
    """Crea un nuevo servidor."""
    db = SessionLocal()
    try:
        # Si se marca como primario, quitar primario de los demás del mismo tipo
        if req.is_primary:
            db.query(ServerConfig).filter(
                ServerConfig.server_type == req.server_type,
                ServerConfig.is_primary == True
            ).update({"is_primary": False})

        server = ServerConfig(
            name=req.name,
            server_type=req.server_type,
            ip=req.ip,
            domain=req.domain or "",
            admin_user=req.admin_user,
            admin_pass=encrypt_password(req.admin_pass),
            allowed_groups=req.allowed_groups or "",
            is_primary=req.is_primary,
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
                # Quitar primario de los demás del mismo tipo
                db.query(ServerConfig).filter(
                    ServerConfig.server_type == server.server_type,
                    ServerConfig.id != server_id,
                    ServerConfig.is_primary == True
                ).update({"is_primary": False})
            server.is_primary = req.is_primary

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
    """Prueba la conexión a un servidor (LDAP para AD, WMI para Archivos/Impresoras)."""
    db = SessionLocal()
    try:
        server_cfg = db.query(ServerConfig).filter(ServerConfig.id == server_id).first()
        if not server_cfg:
            raise HTTPException(status_code=404, detail="Servidor no encontrado.")

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
            import wmi
            import pythoncom
            pythoncom.CoInitialize()
            try:
                c = wmi.WMI(computer=server_cfg.ip, user=server_cfg.admin_user, password=password)
            except Exception as e:
                if "local connections" in str(e):
                    c = wmi.WMI()
                else:
                    raise
            # Prueba simple para validar credenciales y WMI
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
        if req.server_type in ["da", "ha"]:
            from ldap3 import Server, Connection, ALL
            server = Server(req.ip, get_info=ALL)
            conn = Connection(server, user=req.admin_user, password=req.admin_pass, auto_bind=True)
            conn.unbind()
            return {"success": True, "message": f"Conexión LDAP exitosa a {req.ip}"}
        else:
            import wmi
            import pythoncom
            pythoncom.CoInitialize()
            try:
                c = wmi.WMI(computer=req.ip, user=req.admin_user, password=req.admin_pass)
            except Exception as e:
                if "local connections" in str(e):
                    c = wmi.WMI()
                else:
                    raise
            # Prueba simple para validar credenciales y WMI
            os_info = c.Win32_OperatingSystem()[0]
            return {"success": True, "message": f"Conexión WMI exitosa a {os_info.CSName}"}
    except Exception as e:
        return {"success": False, "message": f"Error de conexión: {str(e)}"}
