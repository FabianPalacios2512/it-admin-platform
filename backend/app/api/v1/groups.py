from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from app.services.graph_service import graph_service
from app.services import ad_service

router = APIRouter()

class GroupMemberRequest(BaseModel):
    username: str
    group_id: str

class AdGroupCreateRequest(BaseModel):
    name: str
    description: str = ""
    scope: str = "Global"
    type: str = "Security"
    path: str

@router.get("/")
async def list_m365_groups():
    """Obtiene la lista de grupos M365 (Seguridad y Teams)."""
    try:
        return await graph_service.get_m365_groups()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ══════════════════════════════════════════════════════════════
# RUTAS DE ACTIVE DIRECTORY (ON-PREMISES)
# ══════════════════════════════════════════════════════════════

@router.get("/ad")
def get_ad_groups():
    """Obtiene todos los grupos locales del AD (con caché de 5 minutos)."""
    try:
        return ad_service.get_ad_groups_cached()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ad")
def create_ad_group(req: AdGroupCreateRequest):
    """Crea un nuevo grupo local en el AD."""
    try:
        result = ad_service.create_ad_group(req.dict())
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        # Invalidar caché de grupos para que la próxima consulta traiga el nuevo grupo
        ad_service.invalidate_groups_cache()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ad/search")
def search_ad_objects(q: str = ""):
    """Busca usuarios y grupos locales para autocompletado."""
    try:
        return ad_service.search_ad_objects(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ad/{group_name}/members")
def get_ad_group_members(group_name: str):
    """Obtiene los miembros de un grupo AD local."""
    try:
        return ad_service.get_ad_group_members(group_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AddMemberRequest(BaseModel):
    member_name: str

@router.post("/ad/{group_name}/members")
def add_ad_group_member(group_name: str, req: AddMemberRequest):
    """Agrega un miembro a un grupo AD local."""
    try:
        result = ad_service.add_ad_group_member(group_name, req.member_name)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/ad/{group_name}/members/{member_name}")
def remove_ad_group_member(group_name: str, member_name: str):
    """Quita un miembro de un grupo AD local."""
    try:
        result = ad_service.remove_ad_group_member(group_name, member_name)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ══════════════════════════════════════════════════════════════
# RUTAS DE MICROSOFT 365
# ══════════════════════════════════════════════════════════════

@router.get("/user/{username}")
async def get_user_m365_groups(username: str):
    """Devuelve los grupos de Microsoft 365 a los que pertenece el usuario."""
    try:
        groups = await graph_service.get_user_m365_groups(username)
        return {"success": True, "data": groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add")
async def add_member(req: GroupMemberRequest):
    """Añade un usuario a un grupo M365."""
    try:
        result = await graph_service.add_user_to_m365_group(req.username, req.group_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al agregar a grupo: {str(e)}")

@router.post("/remove")
async def remove_member(req: GroupMemberRequest):
    """Remueve a un usuario de un grupo M365."""
    try:
        result = await graph_service.remove_user_from_m365_group(req.username, req.group_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al remover de grupo: {str(e)}")
