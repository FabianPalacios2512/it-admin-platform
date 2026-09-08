import asyncio
import sys
import os

# Agrega la raíz del backend al path para que "app." resuelva
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.services.zabbix_service import ZabbixService

async def main():
    service = ZabbixService(url="test", username="test", password="test")
    calls = await service.get_active_calls()
    print("Calls found:", len(calls))
    if calls:
        print(calls[0])

asyncio.run(main())
