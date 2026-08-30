import asyncio
from app.services.graph_service import graph_service

async def main():
    data = await graph_service.get_inactive_licensed_users(90)
    for u in data[:3]:
        print(u["displayName"], u.get("onPremisesSyncEnabled"))

asyncio.run(main())
