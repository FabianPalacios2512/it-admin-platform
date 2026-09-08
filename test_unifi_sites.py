import asyncio
import httpx
from app.core.config import env_settings

async def test():
    url = 'https://glossa.hogarymoda.local:8443/api/login'
    async with httpx.AsyncClient(verify=False, trust_env=False, timeout=5.0) as client:
        payload = {'username': env_settings.UNIFI_USER, 'password': env_settings.UNIFI_PASS}
        res = await client.post(url, json=payload)
        cookies = dict(res.cookies)
        
        url_sites = 'https://glossa.hogarymoda.local:8443/api/self/sites'
        res_sites = await client.get(url_sites, cookies=cookies)
        data = res_sites.json().get('data', [])
        for s in data:
            print(f"Name: {s.get('name')} | Desc: {s.get('desc')}")
test()
