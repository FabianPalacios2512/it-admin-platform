import httpx
from app.core.config import env_settings
import ssl

class UniFiService:
    def __init__(self):
        # La URL base fue indicada explícitamente en el requerimiento
        self.base_url = "https://glossa.hogarymoda.local:8443"
        self.user = env_settings.UNIFI_USER
        self.password = env_settings.UNIFI_PASS
        # Aquí guardaremos las cookies después del login
        self.cookies = {}
        self.headers = {}

    def _get_client(self):
        # trust_env=False asegura que no usemos proxies configurados a nivel del SO
        # que a veces bloquean conexiones locales. verify=False es el "-k" de curl.
        return httpx.AsyncClient(verify=False, trust_env=False)

    async def login(self):
        url = f"{self.base_url}/api/login"
        payload = {"username": self.user, "password": self.password}
        
        async with self._get_client() as client:
            try:
                # El "json=payload" agrega automáticamente Content-Type: application/json
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise Exception(f"No se pudo iniciar sesión. Status: {res.status_code}")
                
                # Extraemos la cookie generada y la guardamos manualmente
                self.cookies = dict(res.cookies)
                self.headers = {}
                if 'x-csrf-token' in res.headers:
                    self.headers['X-CSRF-Token'] = res.headers['x-csrf-token']
                return True
            except Exception as e:
                print(f"🔥 DEBUG UNIFI LOGIN ERROR: {str(e)}")
                raise Exception(f"No se pudo iniciar sesión en el controlador UniFi: {str(e)}")

    async def get_sites(self):
        await self.login()
        url = f"{self.base_url}/api/self/sites"
        async with self._get_client() as client:
            res = await client.get(url, cookies=self.cookies)
            res.raise_for_status()
            data = res.json().get("data", [])
            return [{"desc": site.get("desc"), "name": site.get("name")} for site in data]

    async def get_devices(self, site_name: str):
        await self.login()
        url = f"{self.base_url}/api/s/{site_name}/stat/device"
        async with self._get_client() as client:
            res = await client.get(url, cookies=self.cookies)
            res.raise_for_status()
            data = res.json()
            return data.get("data", [])

    async def get_clients(self, site_name: str):
        await self.login()
        url = f"{self.base_url}/api/s/{site_name}/stat/sta"
        async with self._get_client() as client:
            res = await client.get(url, cookies=self.cookies)
            res.raise_for_status()
            data = res.json()
            return data.get("data", [])

    async def get_all_clients(self, site_name: str):
        await self.login()
        url = f"{self.base_url}/api/s/{site_name}/stat/alluser"
        async with self._get_client() as client:
            res = await client.get(url, cookies=self.cookies)
            res.raise_for_status()
            data = res.json()
            return data.get("data", [])

    async def restart_ap(self, mac: str, site_name: str = "default"):
        await self.login()
        url = f"{self.base_url}/api/s/{site_name}/cmd/devmgr"
        payload = {"cmd": "restart", "mac": mac}
        async with self._get_client() as client:
            res = await client.post(url, json=payload, cookies=self.cookies, headers=self.headers)
            res.raise_for_status()
            return res.json()

    async def block_client(self, mac: str, site_name: str = "default"):
        await self.login()
        url = f"{self.base_url}/api/s/{site_name}/cmd/stamgr"
        payload = {"cmd": "block-sta", "mac": mac}
        async with self._get_client() as client:
            res = await client.post(url, json=payload, cookies=self.cookies, headers=self.headers)
            res.raise_for_status()
            return res.json()

    async def unblock_client(self, mac: str, site_name: str = "default"):
        await self.login()
        url = f"{self.base_url}/api/s/{site_name}/cmd/stamgr"
        payload = {"cmd": "unblock-sta", "mac": mac}
        async with self._get_client() as client:
            res = await client.post(url, json=payload, cookies=self.cookies, headers=self.headers)
            res.raise_for_status()
            return res.json()

    async def close(self):
        pass # Ya no necesitamos close manual

# Instancia singleton
unifi_service = UniFiService()
