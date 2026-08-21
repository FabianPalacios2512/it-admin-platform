from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.services.fs_service import get_shared_folders, browse_folder
from app.services.fs_acl_service import get_acl, add_acl, remove_acl
from app.services.ad_service import search_users, search_ad_groups
from app.core.config import get_primary_server
from pydantic import BaseModel
from app.core.database import SessionLocal
from app.models.audit import AuditLog

router = APIRouter()

class ACLRequest(BaseModel):
    account: str
    permission: str = "ReadAndExecute" # ReadAndExecute, Modify, FullControl
    subpath: str = ""
    admin_user: str = "Sistema"

class ACLRemoveRequest(BaseModel):
    account: str
    subpath: str = ""
    admin_user: str = "Sistema"

class CreateFolderRequest(BaseModel):
    folder_name: str
    base_path: str = ""
    inherit_permissions: bool = True
    admin_user: str = "Sistema"

class CloudShareRequest(BaseModel):
    path: str = ""

@router.get("/shares", response_model=List[Dict[str, Any]])
def list_shared_folders():
    """Lista las carpetas compartidas del servidor de archivos."""
    try:
        return get_shared_folders()
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shares/{share_name}/browse", response_model=List[Dict[str, Any]])
def browse_share(share_name: str, path: str = ""):
    """Navega por una carpeta compartida y devuelve sus archivos/subcarpetas."""
    try:
        return browse_folder(share_name, path)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shares/{share_name}/acl", response_model=List[Dict[str, Any]])
def get_share_acl(share_name: str, path: str = ""):
    """Obtiene los permisos NTFS de una ruta."""
    try:
        return get_acl(share_name, path)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shares/{share_name}/acl/add")
def add_share_acl(share_name: str, req: ACLRequest):
    """Agrega o modifica un permiso en una ruta."""
    try:
        add_acl(share_name, req.subpath, req.account, req.permission)
        db = SessionLocal()
        db.add(AuditLog(
            username=req.admin_user,
            action=f"Asignó permiso ({req.permission})",
            target=f"{share_name}\\{req.subpath} -> {req.account}",
            status="Completado",
            source="Web"
        ))
        db.commit()
        db.close()
        return {"success": True, "message": "Permiso agregado correctamente."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shares/{share_name}/acl/remove")
def remove_share_acl(share_name: str, req: ACLRemoveRequest):
    """Elimina todos los permisos de una cuenta en una ruta."""
    try:
        remove_acl(share_name, req.subpath, req.account)
        db = SessionLocal()
        db.add(AuditLog(
            username=req.admin_user,
            action="Removió permisos",
            target=f"{share_name}\\{req.subpath} -> {req.account}",
            status="Completado",
            source="Web"
        ))
        db.commit()
        db.close()
        return {"success": True, "message": "Permiso eliminado correctamente."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class BreakInheritanceRequest(BaseModel):
    subpath: str = ""
    admin_user: str = "Sistema"

@router.post("/shares/{share_name}/acl/break-inheritance")
def break_share_inheritance(share_name: str, req: BreakInheritanceRequest):
    """Deshabilita la herencia de una carpeta y copia los permisos."""
    from app.services.fs_acl_service import disable_inheritance_and_copy
    try:
        disable_inheritance_and_copy(share_name, req.subpath)
        db = SessionLocal()
        db.add(AuditLog(
            username=req.admin_user,
            action="Rompió herencia de carpeta",
            target=f"{share_name}\\{req.subpath}",
            status="Completado",
            source="Web"
        ))
        db.commit()
        db.close()
        return {"success": True, "message": "Herencia deshabilitada correctamente."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shares/{share_name}/folders")
def create_folder(share_name: str, req: CreateFolderRequest):
    """Crea una nueva carpeta en el servidor de archivos (PowerShell)."""
    from app.services.fs_acl_service import create_folder as fs_create_folder
    try:
        fs_create_folder(share_name, req.base_path, req.folder_name, req.inherit_permissions)
        db = SessionLocal()
        db.add(AuditLog(
            username=req.admin_user,
            action="Creó carpeta",
            target=f"{share_name}\\{req.base_path}\\{req.folder_name}",
            status="Completado",
            source="Web"
        ))
        db.commit()
        db.close()
        return {"success": True, "message": f"Carpeta '{req.folder_name}' creada."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shares/{share_name}/effective-access")
def audit_access(share_name: str, path: str = ""):
    """Audita los accesos efectivos de una carpeta usando Get-Acl."""
    from app.services.fs_acl_service import audit_effective_access
    try:
        data = audit_effective_access(share_name, path)
        return {"success": True, "data": data}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shares/{share_name}/share-cloud")
def share_cloud(share_name: str, req: CloudShareRequest):
    """Integra con MS Graph para crear un enlace público de M365 (Stub)."""
    try:
        # TODO: Implementar lógica de MS Graph para crear un link público en OneDrive/SharePoint
        # y mapear el archivo físico local al espacio de la nube del usuario.
        return {
            "success": True,
            "link": f"https://m365.example.com/share/{share_name}/{req.path}?token=mock123",
            "message": "Enlace generado en la nube (Stub)."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search-ad")
def search_ad_for_acl(q: str = "", limit: int = 15):
    """
    Busca usuarios Y grupos en el Directorio Activo para agregar permisos.
    Devuelve resultados con el formato DOMINIO\\sAMAccountName listo para inyectar como ACL.
    """
    if len(q) < 2:
        return []
    try:
        # Obtener el dominio del DA principal
        da_cfg = get_primary_server("da")
        domain_parts = da_cfg["domain"].split(".")
        netbios_domain = domain_parts[0].upper()  # code.local -> CODE

        results = []

        # Buscar GRUPOS
        try:
            groups = search_ad_groups(q, limit)
            for g in groups:
                results.append({
                    "name": g["name"],
                    "samaccountname": g.get("name", ""),
                    "ntaccount": f"{netbios_domain}\\{g['name']}",
                    "description": g.get("description", ""),
                    "type": "Grupo",
                    "icon": "group"
                })
        except Exception as e:
            print(f"⚠️ [FS Search] Error buscando grupos: {e}")

        # Buscar USUARIOS
        try:
            users = search_users(q, limit)
            for u in users:
                results.append({
                    "name": u.get("fullName", u["username"]),
                    "samaccountname": u["username"],
                    "ntaccount": f"{netbios_domain}\\{u['username']}",
                    "description": u.get("title", "") or u.get("department", ""),
                    "type": "Usuario",
                    "icon": "user"
                })
        except Exception as e:
            print(f"⚠️ [FS Search] Error buscando usuarios: {e}")

        return results[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ClonePreviewRequest(BaseModel):
    source_user: str
    target_user: str

@router.post("/clone-preview")
def preview_clone_permissions(req: ClonePreviewRequest):
    """Devuelve el delta de permisos (qué ganará el destino)."""
    from app.services.fs_acl_service import calculate_permission_delta
    try:
        delta = calculate_permission_delta(req.source_user, req.target_user)
        return {"success": True, "delta": delta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CloneExecuteRequest(BaseModel):
    source_user: str
    target_user: str
    delta: dict
    admin_user: str = "Sistema"

from fastapi import BackgroundTasks

@router.post("/clone-execute")
def execute_clone_permissions(req: CloneExecuteRequest, background_tasks: BackgroundTasks):
    """Ejecuta la clonación de permisos usando el delta en segundo plano."""
    from app.services.fs_acl_service import execute_clone_delta
    from app.core.task_manager import create_task, run_async_task
    try:
        # 1. Crear el registro de la tarea
        description = f"Clonando permisos de {req.source_user} a {req.target_user}"
        task_id = create_task("clone_permissions", req.admin_user, description)
        
        # 2. Enviar a segundo plano
        background_tasks.add_task(run_async_task, task_id, execute_clone_delta, req.target_user, req.delta, req.admin_user)
        
        # 3. Retornar inmediatamente
        return {"success": True, "message": "Clonación iniciada en segundo plano", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
