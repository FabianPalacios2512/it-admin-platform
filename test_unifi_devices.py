import asyncio
import httpx
from app.core.config import env_settings

async def test():
    url = 'https://glossa.hogarymoda.local:8443/api/login'
    try:
        async with httpx.AsyncClient(verify=False, trust_env=False, timeout=5.0) as client:
            payload = {'username': env_settings.UNIFI_USER, 'password': env_settings.UNIFI_PASS}
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                cookies = dict(res.cookies)
                
                # Fetch devices on q0zet7qu
                url_dev = 'https://glossa.hogarymoda.local:8443/api/s/q0zet7qu/stat/device'
                res_dev = await client.get(url_dev, cookies=cookies)
                data = res_dev.json().get('data', [])
                
                print(f"Total devices in q0zet7qu: {len(data)}")
                for d in data[:5]:
                    state = d.get('state')
                    print(f"- {d.get('name')} | State: {state} | IP: {d.get('ip')}")
                    
                # Try fetching devices on uzx8k4br
                url_dev2 = 'https://glossa.hogarymoda.local:8443/api/s/uzx8k4br/stat/device'
                res_dev2 = await client.get(url_dev2, cookies=cookies)
                data2 = res_dev2.json().get('data', [])
                
                print(f"Total devices in uzx8k4br: {len(data2)}")
                for d in data2[:5]:
                    state = d.get('state')
                    print(f"- {d.get('name')} | State: {state} | IP: {d.get('ip')}")
                    
    except Exception as e:
        print(f'ERROR: {e}')

asyncio.run(test())
