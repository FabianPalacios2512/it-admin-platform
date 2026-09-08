import asyncio
import httpx
from app.core.config import env_settings

async def test():
    url = 'https://glossa.hogarymoda.local:8443/api/login'
    try:
        async with httpx.AsyncClient(verify=False, trust_env=False, timeout=2.0) as client:
            payload = {'username': env_settings.UNIFI_USER, 'password': env_settings.UNIFI_PASS}
            res = await client.post(url, json=payload)
            print(f'{url} -> {res.status_code}')
            print(res.text)
            
            if res.status_code == 200:
                cookies = dict(res.cookies)
                headers = {}
                if 'x-csrf-token' in res.headers:
                    headers['X-CSRF-Token'] = res.headers['x-csrf-token']
                
                # Fetch devices on q0zet7qu
                url_dev = 'https://glossa.hogarymoda.local:8443/api/s/q0zet7qu/stat/device'
                res_dev = await client.get(url_dev, cookies=cookies)
                print(f'Devices -> {res_dev.status_code}')
                # print(res_dev.text[:200])
    except Exception as e:
        print(f'{url} -> ERROR: {e}')

asyncio.run(test())
