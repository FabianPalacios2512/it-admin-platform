from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from app.services.graph_service import graph_service

router = APIRouter()

class GroupMemberRequest(BaseModel):
    username: str
    group_id: str

@router.get("/")
async def list_m365_groups():
    """Obtiene la lista de grupos M365 (Seguridad y Teams)."""
    try:
        return await graph_service.get_m365_groups()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
