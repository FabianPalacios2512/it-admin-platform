import asyncio
import httpx

async def test():
    urls = [
        'http://127.0.0.1:8080/api/login',
        'https://127.0.0.1:8443/api/login',
        'https://glossa.hogarymoda.local:8443/api/login'
    ]
    for url in urls:
        try:
            async with httpx.AsyncClient(verify=False, trust_env=False, timeout=2.0) as client:
                res = await client.post(url, json={'username': 'admin', 'password': 'password'})
                print(f'{url} -> {res.status_code}')
        except Exception as e:
            print(f'{url} -> ERROR: {type(e).__name__}')

asyncio.run(test())
