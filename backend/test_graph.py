import asyncio
from app.services.graph_service import graph_service

async def main():
    token = await graph_service._get_access_token()
    print("Token obtained")
    # Fetch Alejandro
    data = await graph_service._request("GET", "/users/alejandro.cardenas@hogarymoda.com.co?$select=id,displayName,userPrincipalName,onPremisesSyncEnabled,signInActivity")
    print("Raw Alejandro Data:")
    print(data)

asyncio.run(main())
