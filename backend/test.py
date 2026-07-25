import asyncio, sys
sys.path.append('.')
from app.services.unifi_service import unifi_service
async def main():
    users = await unifi_service.get_all_clients('q0zet7qu')
    blocked = [u for u in users if u.get('blocked') or u.get('is_blocked')]
    print(f'Total users: {len(users)}, Blocked: {len(blocked)}')
    if blocked:
        print(blocked[0])
asyncio.run(main())
