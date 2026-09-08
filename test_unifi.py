import asyncio
from app.services.unifi_service import unifi_service

async def main():
    print('Intentando login...')
    await unifi_service.login()
    print('Login exitoso. Obteniendo sitios...')
    sites = await unifi_service.get_sites()
    print(f'Sitios: {sites}')
    
    print('Obteniendo dispositivos del sitio q0zet7qu...')
    devices = await unifi_service.get_devices('q0zet7qu')
    for d in devices:
        print(f"AP: {d.get('name') or d.get('mac')} - Estado: {d.get('state')} - IP: {d.get('ip')}")

if __name__ == '__main__':
    asyncio.run(main())
