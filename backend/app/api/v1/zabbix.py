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

import os
import json
import asyncio

import subprocess

@router.get("/fortigates")
def get_fortigates_data(current_user: dict = Depends(get_current_user)):
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        ps1_path = os.path.join(base_dir, "scripts", "Get-ZabbixFortigates.ps1")
        output_path = os.path.join(base_dir, "scripts", "fortigates_data.json")
        
        # Ejecutamos el script de PowerShell sincrónicamente (es más estable en Windows/uvicorn)
        cmd = [
            "powershell.exe", "-ExecutionPolicy", "Bypass", 
            "-File", ps1_path, 
            "-ZabbixURL", os.getenv("ZABBIX_URL"),
            "-ZabbixUser", os.getenv("ZABBIX_USER"),
            "-ZabbixPass", os.getenv("ZABBIX_PASSWORD"),
            "-OutputFile", output_path
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            logger.error(f"PowerShell Script Failed: {process.stderr}")
            raise Exception(f"PowerShell script failed: {process.stderr}")
            
        if os.path.exists(output_path):
            with open(output_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            return data
        else:
            return []
            
    except Exception as e:
        logger.exception(f"Error executing PS1 script: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
