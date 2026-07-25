import asyncio, sys, json
sys.path.append('.')
from app.services.unifi_service import unifi_service
async def main():
    devices = await unifi_service.get_devices('q0zet7qu')
    if devices:
        d = devices[0]
        keys = [k for k in d.keys() if 'sta' in k or 'user' in k or 'sat' in k or 'client' in k]
        print("Keys:", keys)
        print("Satisfaction:", d.get('satisfaction'))
        print("Num_sta:", d.get('num_sta'))
        print("user_num_sta:", d.get('user-wlan-num_sta', d.get('user-num_sta')))
asyncio.run(main())
