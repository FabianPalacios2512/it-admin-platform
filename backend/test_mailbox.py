import asyncio
import sys
import os

sys.path.append(os.getcwd())
from app.services.graph_service import graph_service

async def main():
    try:
        user_id = await graph_service.resolve_user_id("fapaternina")
        print("User ID:", user_id)
        endpoint = f"/users/{user_id}/mailboxSettings"
        data = await graph_service._request("GET", endpoint)
        print("Mailbox Settings direct:", data)
    except Exception as e:
        print("Error mailboxSettings:", str(e))
        
    try:
        endpoint2 = f"/users/{user_id}?$select=mailboxSettings"
        data2 = await graph_service._request("GET", endpoint2)
        print("User with select mailboxSettings:", data2)
    except Exception as e:
        print("Error select:", str(e))

if __name__ == "__main__":
    asyncio.run(main())
