from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from app.services.ad_service import (
    search_users,
    get_user_profile,
    get_locked_accounts,
    unlock_account,
    reset_password,
    get_account_options,
    get_ad_health_stats,
    update_account_options,
    get_all_attributes,
    update_attribute,
    update_attributes_bulk,
    get_folder_groups,
    get_organizational_units,
    create_ad_user,
    search_ad_groups,
    add_user_to_group,
    remove_user_from_group,
)
from app.services.fs_acl_service import get_user_effective_folders
from app.core.database import get_db, SessionLocal
from app.models.audit import AuditLog

router = APIRouter()


# ══════════════════════════════════════════════════════════════
# ESQUEMAS
# ══════════════════════════════════════════════════════════════
class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str
    must_change: bool = True
    admin_user: Optional[str] = "Sistema"

class UnlockRequest(BaseModel):
    username: str
    admin_user: Optional[str] = "Sistema"

class AccountOptionsRequest(BaseModel):
    username: str
    options: dict
    admin_user: Optional[str] = "Sistema"

class UpdateAttributeRequest(BaseModel):
    username: str
    attr_name: str
    new_value: str
    admin_user: Optional[str] = "Sistema"

class BulkEditRequest(BaseModel):
    username: str
    updates: dict
    admin_user: Optional[str] = "Sistema"

class CreateUserRequest(BaseModel):
    firstName: str
    lastName: str
    initials: Optional[str] = ""
    fullName: str
    upn: str
    samAccountName: str
    accountType: Optional[str] = "onpremise"
    ou: Optional[str] = ""
    password: str
    mustChangePassword: bool = True
    cannotChangePassword: bool = False
    passwordNeverExpires: bool = False
    accountDisabled: bool = False
    description: str
    jobTitle: Optional[str] = ""
    department: Optional[str] = ""
    managerDn: Optional[str] = ""
    telephoneNumber: Optional[str] = ""
    admin_user: Optional[str] = "Sistema"

class GroupMembershipRequest(BaseModel):
    username: str
    group_dn: str
    admin_user: Optional[str] = "Sistema"


# ══════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/search")
async def api_search_users(q: str = "", limit: int = 50):
    """Busca usuarios en el Directorio Activo y Entra ID por nombre, usuario o correo."""
    from fastapi.concurrency import run_in_threadpool
    from app.services.graph_service import graph_service
    
    try:
        search_q = q if q else "*"
        
        # 1. Buscar en AD local (Síncrono, se corre en threadpool)
        ad_results = await run_in_threadpool(search_users, search_q, limit)
        
        # 2. Buscar en Microsoft Entra ID (Nube)
        cloud_results = await graph_service.search_cloud_users(search_q, limit)
        
        # 3. Fusionar evitando duplicados (priorizando AD Local si ya existe)
        ad_usernames = {u.get("username", "").lower() for u in ad_results if u.get("username")}
        ad_upns = {u.get("userPrincipalName", "").lower() for u in ad_results if u.get("userPrincipalName")}
        
        merged_results = list(ad_results)
        
        for cu in cloud_results:
            cu_uname = cu.get("username", "").lower()
            cu_upn = cu.get("userPrincipalName", "").lower()
            
            # Si el usuario NO está en AD local, lo añadimos
            if cu_uname and cu_uname not in ad_usernames and cu_upn not in ad_upns:
                merged_results.append(cu)
                
        # Opcional: ordenar alfabéticamente
        merged_results.sort(key=lambda x: x.get("fullName", "").lower())
        
        return merged_results[:limit] if len(merged_results) > limit else merged_results
    except Exception as e:
        print(f"[ERROR] [BÚSQUEDA] Error unificado: {e}")
        raise HTTPException(status_code=500, detail=f"Error consultando usuarios: {str(e)}")


@router.get("/profile/{username}")
async def api_get_user_profile(username: str):
    """Obtiene el perfil completo 360 de un usuario desde el AD o Entra ID si es solo nube."""
    from fastapi.concurrency import run_in_threadpool
    from app.services.graph_service import graph_service
    
    try:
        profile = await run_in_threadpool(get_user_profile, username)
        if profile is None:
            # Fallback a Graph (Usuario Solo Nube)
            profile = await graph_service.get_cloud_user_profile(username)
            if not profile:
                raise HTTPException(status_code=404, detail=f"Usuario '{username}' no encontrado en el Directorio Activo ni en la Nube.")
            
        return profile
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [AD] Error obteniendo perfil: {e}")
        raise HTTPException(status_code=500, detail=f"Error consultando perfil: {str(e)}")


@router.get("/diagnose/{username}")
async def api_diagnose_user(username: str):
    """Realiza un diagnóstico rápido (Triage) del usuario consultando AD y Entra ID."""
    from app.services.graph_service import graph_service
    import datetime

    diagnosis = {
        "ad_status": "unknown",
        "ad_issues": [],
        "entra_status": "unknown",
        "entra_issues": [],
        "licenses": []
    }

    # 1. Active Directory Local
    try:
        options = get_account_options(username)
        if not options:
            diagnosis["ad_status"] = "error"
            diagnosis["ad_issues"].append("Usuario no encontrado en AD local.")
        else:
            issues = []
            if options.get("account_locked"):
                issues.append("Cuenta BLOQUEADA en AD.")
            if options.get("account_disabled"):
                issues.append("Cuenta DESHABILITADA en AD.")
            if options.get("must_change_password"):
                issues.append("Debe cambiar contraseña al iniciar sesión.")
            
            # Check expiration date if any
            if not options.get("password_never_expires"):
                # Approximate password expiration check could go here if we fetch pwdLastSet and domain policy
                # For now just note it
                pass
            
            diagnosis["ad_issues"] = issues
            diagnosis["ad_status"] = "error" if issues else "ok"
    except Exception as e:
        diagnosis["ad_status"] = "error"
        diagnosis["ad_issues"].append(f"Error consultando AD: {str(e)}")

    # 2. Microsoft Entra ID (Graph API)
    try:
        user_id = await graph_service.resolve_user_id(username)
        user_info = await graph_service.get_user_info_and_licenses(user_id)
        
        graph_issues = []
        if not user_info.get("accountEnabled", True):
            graph_issues.append("Cuenta DESHABILITADA en M365/Entra ID.")
            
        licenses = user_info.get("licenses", [])
        diagnosis["licenses"] = [lic.get("skuId") for lic in licenses]
        if not licenses:
            graph_issues.append("No tiene licencias de M365 asignadas.")
            
        diagnosis["entra_issues"] = graph_issues
        diagnosis["entra_status"] = "error" if graph_issues else "ok"
    except Exception as e:
        diagnosis["entra_status"] = "error"
        diagnosis["entra_issues"].append(f"No se pudo consultar Entra ID (¿Sincronizado?): {str(e)}")

    return diagnosis



@router.get("/locked")
def api_get_locked_accounts():
    """Obtiene todas las cuentas bloqueadas en tiempo real desde el AD."""
    try:
        locked = get_locked_accounts()
        return locked
    except Exception as e:
        print(f"❌ [AD] Error buscando cuentas bloqueadas: {e}")
        raise HTTPException(status_code=500, detail=f"Error consultando el AD: {str(e)}")


@router.post("/unlock")
def api_unlock_account(req: UnlockRequest):
    """Desbloquea una cuenta de AD."""
    try:
        result = unlock_account(req.username)
        if result["success"]:
            # Registrar en auditoría
            db = SessionLocal()
            audit = AuditLog(
                username=req.admin_user,
                action="Desbloqueó cuenta",
                target=req.username,
                status="Completado",
                source="Web",
            )
            db.add(audit)
            db.commit()
            db.close()
        return result
    except Exception as e:
        print(f"❌ [AD] Error desbloqueando: {e}")
        raise HTTPException(status_code=500, detail=f"Error al desbloquear: {str(e)}")


@router.post("/reset-password")
def api_reset_password(req: ResetPasswordRequest):
    """Resetea la contraseña de un usuario en el AD."""
    try:
        result = reset_password(req.username, req.new_password, req.must_change)
        if result["success"]:
            # Registrar en auditoría
            db = SessionLocal()
            audit = AuditLog(
                username=req.admin_user,
                action="Reseteo contraseña",
                target=req.username,
                status="Completado",
                source="Web",
            )
            db.add(audit)
            db.commit()
            db.close()
        return result
    except Exception as e:
        print(f"❌ [AD] Error reseteando clave: {e}")
        raise HTTPException(status_code=500, detail=f"Error al resetear: {str(e)}")

@router.post("/quick-reset-password")
def api_quick_reset_password(req: UnlockRequest):
    """Genera una contraseña temporal y la resetea forzando cambio al inicio."""
    try:
        from app.services.ad_service import reset_ad_password
        result = reset_ad_password(req.username)
        if result.get("success"):
            db = SessionLocal()
            audit = AuditLog(
                username=req.admin_user,
                action="Quick Reset Password",
                target=req.username,
                status="Completado",
                source="Web",
            )
            db.add(audit)
            db.commit()
            db.close()
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al resetear: {str(e)}")


class ProxyAddressRequest(BaseModel):
    username: str
    alias: str
    action: str
    admin_user: Optional[str] = "Sistema"

@router.post("/proxy-addresses")
def api_manage_proxy_address(req: ProxyAddressRequest):
    """Añade o remueve un alias de correo (proxyAddresses)."""
    try:
        from app.services.ad_service import manage_proxy_address
        result = manage_proxy_address(req.username, req.alias, req.action)
        if result.get("success"):
            db = SessionLocal()
            audit = AuditLog(
                username=req.admin_user,
                action=f"{'Agregó' if req.action=='add' else 'Removió'} alias",
                target=f"{req.username} ({req.alias})",
                status="Completado",
                source="Web",
            )
            db.add(audit)
            db.commit()
            db.close()
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error gestionando alias: {str(e)}")


@router.post("/offboard/{username}")
async def api_offboard_user(username: str):
    """Ejecuta la baja automática de 1-click."""
    admin_user = "Sistema"
    results = []
    
    # 1. Disable AD Account
    try:
        from app.services.ad_service import update_account_options
        ad_res = update_account_options(username, {"account_disabled": True})
        if ad_res.get("success"):
            results.append("Cuenta AD deshabilitada.")
        else:
            results.append(f"AD Error: {ad_res.get('error')}")
    except Exception as e:
        results.append(f"AD Error: {str(e)}")
        
    # 2. Revoke Sessions
    try:
        from app.services.graph_service import graph_service
        await graph_service.revoke_user_sessions(username)
        results.append("Sesiones de Entra ID revocadas.")
    except Exception as e:
        results.append(f"Graph Error (Sesiones): {str(e)}")
            
    # 3. Remove Licenses
    try:
        from app.services.graph_service import graph_service
        lic_res = await graph_service.remove_all_licenses(username)
        if lic_res.get("success"):
            results.append("Licencias de Microsoft 365 removidas.")
            # Bust the cache for license summary
            from app.services.graph_service import _license_summary_cache
            _license_summary_cache["data"] = {}
            _license_summary_cache["time"] = 0
        else:
            results.append(f"M365 Info: {lic_res.get('message')}")
    except Exception as e:
        results.append(f"Graph Error (Licencias): {str(e)}")
        
    # 4. Exchange Script
    upn = f"{username}@105code.cloud"  # o el dominio por defecto
    ps_script = f"Set-Mailbox -Identity {upn} -Type Shared"
    
    db = SessionLocal()
    audit = AuditLog(
        username=admin_user,
        action="Offboarding Automático",
        target=username,
        status="Completado",
        source="Web",
    )
    db.add(audit)
    db.commit()
    db.close()
    
    return {
        "success": True,
        "message": "Offboarding ejecutado.",
        "results": results,
        "exchange_script": ps_script
    }

@router.post("/attributes")
def api_update_attribute(req: UpdateAttributeRequest):
    """Actualiza un atributo LDAP específico del usuario."""
    try:
        result = update_attribute(req.username, req.attr_name, req.new_value)
        if result.get("success"):
            db = SessionLocal()
            audit = AuditLog(
                username=req.admin_user,
                action=f"Edit atributo AD: {req.attr_name}",
                target=req.username,
                status="Completado",
                source="Web",
            )
            db.add(audit)
            db.commit()
            db.close()
        return result
    except Exception as e:
        print(f"❌ [AD] Error actualizando atributo: {e}")
        raise HTTPException(status_code=500, detail=f"Error actualizando atributo: {str(e)}")


@router.post("/profile/bulk-edit")
def api_bulk_edit_profile(req: BulkEditRequest):
    """Actualiza múltiples atributos del perfil del usuario."""
    try:
        result = update_attributes_bulk(req.username, req.updates)
        if result.get("success"):
            db = SessionLocal()
            audit = AuditLog(
                username=req.admin_user,
                action="Edición masiva de perfil",
                target=req.username,
                status="Completado",
                source="Web",
            )
            db.add(audit)
            db.commit()
            db.close()
        return result
    except Exception as e:
        print(f"❌ [AD] Error en bulk edit: {e}")
        raise HTTPException(status_code=500, detail=f"Error actualizando perfil: {str(e)}")


@router.get("/ous")
def api_get_ous():
    """Retorna la lista de Unidades Organizativas (OUs) disponibles."""
    try:
        return get_organizational_units()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
def api_create_user(req: CreateUserRequest):
    """Crea un nuevo usuario en el Directorio Activo o en Entra ID (Nube)."""
    try:
        data = req.dict()
        if req.accountType == "cloud":
            from app.services.graph_service import create_cloud_user
            result = create_cloud_user(data)
        else:
            result = create_ad_user(data)
            
        if result.get("success"):
            # Registrar en auditoría
            db = SessionLocal()
            audit = AuditLog(
                username=req.admin_user,
                action=f"Creación de usuario ({req.accountType})",
                target=req.samAccountName,
                status="Completado",
                source="Web",
            )
            db.add(audit)
            db.commit()
            db.close()
        return result
    except Exception as e:
        print(f"❌ [CREACIÓN] Error creando usuario: {e}")
        raise HTTPException(status_code=500, detail=f"Error creando usuario: {str(e)}")


@router.get("/account-options/{username}")
def api_get_account_options(username: str):
    """Retorna las opciones de cuenta (flags UAC) del usuario."""
    try:
        opts = get_account_options(username)
        if not opts:
            raise HTTPException(status_code=404, detail=f"Usuario '{username}' no encontrado.")
        return opts
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/account-options")
def api_update_account_options(req: AccountOptionsRequest):
    """Actualiza las opciones de cuenta (flags UAC) del usuario."""
    try:
        result = update_account_options(req.username, req.options)
        if result["success"]:
            db = SessionLocal()
            db.add(AuditLog(
                username=req.admin_user,
                action="Modificación de opciones de cuenta",
                target=req.username,
                status="Completado",
                source="Web",
            ))
            db.commit()
            db.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/attributes/{username}")
def api_get_attributes(username: str):
    """Retorna todos los atributos LDAP del usuario (Editor de atributos)."""
    try:
        attrs = get_all_attributes(username)
        if not attrs:
            raise HTTPException(status_code=404, detail=f"Usuario '{username}' no encontrado.")
        return attrs
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folders/{username}")
def api_get_folder_groups(username: str):
    """Retorna las carpetas y permisos reales asignados al usuario."""
    try:
        # En vez de get_folder_groups de AD, usamos el escáner real del File Server
        return get_user_effective_folders(username)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups/search")
def api_search_groups(q: str = "", limit: int = 20):
    """Busca grupos de seguridad en el AD."""
    if len(q) < 1:
        return []
    try:
        return search_ad_groups(q, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/groups/add")
def api_add_to_group(req: GroupMembershipRequest):
    """Agrega un usuario a un grupo del AD."""
    try:
        result = add_user_to_group(req.username, req.group_dn)
        if result.get("success"):
            db = SessionLocal()
            group_name = req.group_dn.split(",")[0].replace("CN=", "")
            db.add(AuditLog(
                username=req.admin_user,
                action=f"Agregado al grupo: {group_name}",
                target=req.username,
                status="Completado",
                source="Web",
            ))
            db.commit()
            db.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/groups/remove")
def api_remove_from_group(req: GroupMembershipRequest):
    """Quita un usuario de un grupo del AD."""
    try:
        result = remove_user_from_group(req.username, req.group_dn)
        if result.get("success"):
            db = SessionLocal()
            group_name = req.group_dn.split(",")[0].replace("CN=", "")
            db.add(AuditLog(
                username=req.admin_user,
                action=f"Removido del grupo: {group_name}",
                target=req.username,
                status="Completado",
                source="Web",
            ))
            db.commit()
            db.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health-stats")
def api_get_ad_health_stats():
    """Obtiene métricas de salud en vivo del AD."""
    try:
        stats = get_ad_health_stats()
        return stats
    except Exception as e:
        print(f"❌ [AD] Error obteniendo salud del AD: {e}")
        raise HTTPException(status_code=500, detail=f"Error consultando el AD: {str(e)}")
