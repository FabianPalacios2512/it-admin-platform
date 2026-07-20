import httpx
from app.core.config import env_settings
import ssl

class UniFiService:
    def __init__(self):
        self.host = env_settings.UNIFI_HOST
        self.port = env_settings.UNIFI_PORT
        self.user = env_settings.UNIFI_USER
        self.password = env_settings.UNIFI_PASS
        self.site = env_settings.UNIFI_SITE
        self.base_url = f"https://{self.host}:{self.port}"
        self.client = httpx.AsyncClient(verify=False)

    async def login(self):
        url = f"{self.base_url}/api/login"
        payload = {"username": self.user, "password": self.password}
        res = await self.client.post(url, json=payload)
        if res.status_code != 200:
            raise Exception("No se pudo iniciar sesión en el controlador UniFi.")
        return True

    async def get_devices(self):
        await self.login()
        url = f"{self.base_url}/api/s/{self.site}/stat/device"
        res = await self.client.get(url)
        res.raise_for_status()
        data = res.json()
        return data.get("data", [])

    async def restart_ap(self, mac: str):
        await self.login()
        url = f"{self.base_url}/api/s/{self.site}/cmd/devmgr"
        payload = {"cmd": "restart", "mac": mac}
        res = await self.client.post(url, json=payload)
        res.raise_for_status()
        return res.json()

    async def get_all_users(self):
        await self.login()
        url = f"{self.base_url}/api/s/{self.site}/stat/alluser"
        res = await self.client.get(url)
        res.raise_for_status()
        data = res.json()
        return data.get("data", [])

    async def block_client(self, mac: str):
        await self.login()
        url = f"{self.base_url}/api/s/{self.site}/cmd/sitemgr"
        payload = {"cmd": "block-sta", "mac": mac}
        res = await self.client.post(url, json=payload)
        res.raise_for_status()
        return res.json()

    async def unblock_client(self, mac: str):
        await self.login()
        url = f"{self.base_url}/api/s/{self.site}/cmd/sitemgr"
        payload = {"cmd": "unblock-sta", "mac": mac}
        res = await self.client.post(url, json=payload)
        res.raise_for_status()
        return res.json()

    async def close(self):
        await self.client.aclose()

# Instancia singleton para reutilizar la cookie
unifi_service = UniFiService()
