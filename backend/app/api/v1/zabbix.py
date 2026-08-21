from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
from app.services.zabbix_service import ZabbixService
from app.api.v1.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

zabbix_service = ZabbixService(
    url="http://192.168.20.4/api_jsonrpc.php",
    username="Admin",
    password="zabbix"
)

@router.get("/dashboard/summary", response_model=Dict[str, Any])
async def get_zabbix_dashboard_summary(current_user: dict = Depends(get_current_user)):
    try:
        summary = await zabbix_service.get_dashboard_summary()
        return {"status": "success", "data": summary}
    except Exception as e:
        logger.error(f"Error fetching Zabbix summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary: {str(e)}")

@router.get("/dashboard/trends", response_model=Dict[str, Any])
async def get_zabbix_dashboard_trends(time_from: int = None, time_till: int = None, current_user: dict = Depends(get_current_user)):
    try:
        trends = await zabbix_service.get_global_trends(time_from=time_from, time_till=time_till)
        return {"status": "success", "data": trends}
    except Exception as e:
        logger.error(f"Error fetching Zabbix trends: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch trends: {str(e)}")

@router.get("/hosts", response_model=Dict[str, Any])
async def get_zabbix_hosts(time_from: int = None, time_till: int = None, current_user: dict = Depends(get_current_user)):
    try:
        hosts = await zabbix_service.get_all_hosts(time_from=time_from, time_till=time_till)
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
