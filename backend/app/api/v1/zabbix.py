from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
from app.services.zabbix_service import ZabbixService
from app.api.v1.auth import get_current_user
import os

logger = logging.getLogger(__name__)

router = APIRouter()

zabbix_service = ZabbixService(
    url=os.getenv("ZABBIX_URL"),
    username=os.getenv("ZABBIX_USER"),
    password=os.getenv("ZABBIX_PASSWORD")
)

@router.get("/dashboard/summary", response_model=Dict[str, Any])
async def get_zabbix_dashboard_summary(current_user: dict = Depends(get_current_user)):
    try:
        summary = await zabbix_service.get_dashboard_summary()
        return {"status": "success", "data": summary}
    except Exception as e:
        logger.error(f"Error fetching Zabbix summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary: {str(e)}")

@router.get("/groups", response_model=Dict[str, Any])
async def get_zabbix_groups(current_user: dict = Depends(get_current_user)):
    try:
        groups = await zabbix_service.get_host_groups()
        return {"status": "success", "data": groups}
    except Exception as e:
        logger.error(f"Error fetching Zabbix groups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch groups: {str(e)}")

@router.get("/dashboard/trends", response_model=Dict[str, Any])
async def get_zabbix_dashboard_trends(time_from: int = None, time_till: int = None, groupid: str = None, current_user: dict = Depends(get_current_user)):
    try:
        trends = await zabbix_service.get_global_trends(time_from=time_from, time_till=time_till, groupid=groupid)
        return {"status": "success", "data": trends}
    except Exception as e:
        logger.error(f"Error fetching Zabbix trends: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch trends: {str(e)}")

@router.get("/hosts", response_model=Dict[str, Any])
async def get_zabbix_hosts(time_from: int = None, time_till: int = None, groupid: str = None, current_user: dict = Depends(get_current_user)):
    try:
        hosts = await zabbix_service.get_all_hosts(time_from=time_from, time_till=time_till, groupid=groupid)
        return {"status": "success", "data": hosts}
    except Exception as e:
        logger.error(f"Error fetching Zabbix hosts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch hosts: {str(e)}")

@router.get("/metrics/detail", response_model=Dict[str, Any])
async def get_zabbix_metrics_detail(host_id: str, time_range: int = 3600, current_user: dict = Depends(get_current_user)):
    try:
        detail = await zabbix_service.get_host_detail(host_id, time_range=time_range)
        return {"status": "success", "host_id": host_id, "data": detail}
    except Exception as e:
        logger.error(f"Error fetching Zabbix detail for {host_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch host detail: {str(e)}")

@router.get("/pbx", response_model=Dict[str, Any])
async def get_zabbix_pbx_telephony(current_user: dict = Depends(get_current_user)):
    try:
        pbx_data = await zabbix_service.get_pbx_telephony()
        return pbx_data
    except Exception as e:
        logger.error(f"Error fetching PBX data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch PBX data: {str(e)}")

@router.get("/pbx/active-calls", response_model=Dict[str, Any])
async def get_pbx_active_calls(current_user: dict = Depends(get_current_user)):
    """
    Obtiene las llamadas activas en tiempo real via SSH al PBX Issabel.
    Comando ejecutado: asterisk -rx 'core show channels concise' (solo lectura).
    """
    try:
        calls = await zabbix_service.get_active_calls()
        return {"status": "success", "calls": calls, "total": len(calls)}
    except Exception as e:
        logger.error(f"Error fetching active calls: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch active calls: {str(e)}")

import os
import json
import asyncio
import subprocess
from app.services.zabbix_fortigates import get_zabbix_fortigates

@router.get("/fortigates")
async def get_fortigates_data(hostid: str = None, current_user: dict = Depends(get_current_user)):
    try:
        url = os.getenv("ZABBIX_URL")
        user = os.getenv("ZABBIX_USER")
        pwd = os.getenv("ZABBIX_PASSWORD")
        
        return await get_zabbix_fortigates(url, user, pwd, hostid)
    except Exception as e:
        logger.error(f"Error en get_fortigates_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
