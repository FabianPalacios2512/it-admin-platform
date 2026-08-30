import asyncio
from app.services.graph_service import graph_service

async def main():
    token = await graph_service._get_access_token()
    data = await graph_service._request("GET", "/users?$select=id,displayName,userPrincipalName,assignedLicenses,signInActivity,onPremisesSyncEnabled&$top=5")
    for u in data.get("value", []):
        print(u.get("displayName"), u.get("onPremisesSyncEnabled"))

asyncio.run(main())
