import asyncio
import httpx

async def test():
    try:
        url = 'https://127.0.0.1:8443/api/login'
        async with httpx.AsyncClient(verify=False, trust_env=False) as client:
            res = await client.post(url, json={'username': 'admin', 'password': 'password'})
            print(f'Login a 127.0.0.1:8443 status: {res.status_code}')
            print(res.text)
    except Exception as e:
        print(f'Error conectando a 127.0.0.1:8443: {e}')

asyncio.run(test())
