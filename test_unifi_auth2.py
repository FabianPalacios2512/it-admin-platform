import asyncio
import httpx
from app.core.config import env_settings

async def test():
    url = 'https://glossa.hogarymoda.local:8443/api/login'
    try:
        async with httpx.AsyncClient(verify=False, trust_env=False, timeout=2.0) as client:
            payload = {'username': env_settings.UNIFI_USER, 'password': env_settings.UNIFI_PASS, 'remember': True, 'strict': True}
            res = await client.post(url, json=payload)
            print(f'{url} -> {res.status_code}')
            print(res.text)
    except Exception as e:
        print(f'{url} -> ERROR: {e}')

asyncio.run(test())
