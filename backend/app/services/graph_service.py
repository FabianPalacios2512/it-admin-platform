import httpx
import time
from app.core.config import env_settings

_license_summary_cache = {} # Keyed by tenant_id
_subscribed_skus_cache = {} # Keyed by tenant_id
_user_id_cache = {} # Keyed by f"{tenant_id}_{username_lower}"
_LICENSE_CACHE_TTL = 300
_USER_CACHE_TTL = 3600

class MicrosoftGraphService:
    def __init__(self, tenant_id: str = None, client_id: str = None, client_secret: str = None, tenant_name: str = ""):
        self.tenant_id = tenant_id or env_settings.ENTRA_TENANT_ID
        self.client_id = client_id or env_settings.ENTRA_CLIENT_ID
        self.client_secret = client_secret or env_settings.ENTRA_CLIENT_SECRET
        self.tenant_name = tenant_name
        self._token = None
        self._token_expires_at = 0

    async def _get_access_token(self) -> str:
        # Usar token en caché si sigue siendo válido (margen de 5 minutos)
        if self._token and time.time() < self._token_expires_at - 300:
            return self._token

        if not self.tenant_id or not self.client_id or not self.client_secret:
            raise ValueError("Credenciales de Microsoft Graph (ENTRA_*) no configuradas en el entorno (.env).")

        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            if response.status_code != 200:
                print(f"[GraphService] Error auth: {response.text}")
            response.raise_for_status()
            
            token_data = response.json()
            self._token = token_data["access_token"]
            self._token_expires_at = time.time() + token_data.get("expires_in", 3599)
            
            return self._token

    async def _request(self, method: str, endpoint: str, headers: dict = None, api_version: str = "v1.0", **kwargs):
        token = await self._get_access_token()
        headers = headers or {}
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"
        
        url = f"https://graph.microsoft.com/{api_version}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            if response.status_code >= 400:
                print(f"[GraphService] API Error ({endpoint}): {response.text}")
                raise ValueError(f"Graph API Error {response.status_code}: {response.text}")
            if response.status_code == 204:
                return {}
            return response.json()

    async def get_subscribed_skus(self):
        """Termómetro de Licencias"""
        global _subscribed_skus_cache
        cache = _subscribed_skus_cache.setdefault(self.tenant_id, {"time": 0, "data": None})
        if time.time() - cache["time"] < _LICENSE_CACHE_TTL and cache["data"]:
            return cache["data"]
            
        data = await self._request("GET", "/subscribedSkus")
        skus = data.get("value", [])
        
        cache["data"] = skus
        cache["time"] = time.time()
        return skus

    async def get_sync_status(self):
        """Monitor de Sincronización (Entra Connect)"""
        data = await self._request("GET", "/organization?$select=onPremisesLastSyncDateTime")
        value = data.get("value", [])
        if value:
            return value[0].get("onPremisesLastSyncDateTime")
        return None

    async def get_security_alerts(self, status: str = "blocked"):
        """Radar de Seguridad (Inicios de sesión). status puede ser 'blocked', 'success' o 'all'"""
        filter_query = ""
        if status == "blocked":
            filter_query = "$filter=status/errorCode ne 0&"
        elif status == "success":
            filter_query = "$filter=status/errorCode eq 0&"
            
        endpoint = f"/auditLogs/signIns?{filter_query}$orderby=createdDateTime desc&$top=100"
        data = await self._request("GET", endpoint)
        return data.get("value", [])

    async def get_risky_users(self):
        """Usuarios marcados en riesgo por Identity Protection"""
        try:
            data = await self._request("GET", "/identityProtection/riskyUsers?$filter=riskLevel eq 'high' or riskLevel eq 'medium'&$orderby=riskLastUpdatedDateTime desc&$top=50")
            return data.get("value", [])
        except ValueError as e:
            if "403" in str(e) or "Forbidden" in str(e):
                return {"error": "license_required"}
            raise

    async def get_risk_detections(self):
        """Detecciones de riesgo específicas (Viajes imposibles, IP anónima)"""
        try:
            data = await self._request("GET", "/identityProtection/riskDetections?$orderby=detectedDateTime desc&$top=50")
            return data.get("value", [])
        except ValueError as e:
            if "403" in str(e) or "Forbidden" in str(e):
                return {"error": "license_required"}
            raise

    async def revoke_user_sessions(self, username: str):
        """Revoca todas las sesiones de un usuario (Desconectar)"""
        try:
            user_id = await self.resolve_user_id(username)
            await self._request("POST", f"/users/{user_id}/revokeSignInSessions")
            return {"success": True}
        except Exception as e:
            raise ValueError(str(e))

    async def resolve_user_id(self, username: str) -> str:
        """Encuentra el ID del usuario en Entra ID utilizando su username local o UPN."""
        username_lower = username.lower().strip()
        cache_key = f"{self.tenant_id}_{username_lower}"
        
        if cache_key in _user_id_cache:
            if time.time() - _user_id_cache[cache_key]["time"] < _USER_CACHE_TTL:
                cached_id = _user_id_cache[cache_key]["id"]
                if not cached_id:
                    raise ValueError(f"No se encontró el usuario '{username}' en Microsoft Entra ID. Verifica la sincronización.")
                return cached_id
                
        # 1. Intentar acceso directo por UPN (la forma más rápida y segura para UPNs reales)
        if "@" in username_lower:
            try:
                data = await self._request("GET", f"/users/{username_lower}?$select=id,userPrincipalName")
                if data and "id" in data:
                    _user_id_cache[cache_key] = {"id": data["id"], "time": time.time()}
                    return data["id"]
            except Exception:
                pass
                
        headers = {"ConsistencyLevel": "eventual"}
        
        # 2. Intentamos buscar por varios campos (por si enviaron el SAMAccountName o un alias)
        data = await self._request("GET", f"/users?$filter=onPremisesSamAccountName eq '{username_lower}' or userPrincipalName eq '{username_lower}' or mail eq '{username_lower}'&$select=id,userPrincipalName&$count=true", headers=headers)
        if data.get("value"):
            _user_id_cache[cache_key] = {"id": data["value"][0]["id"], "time": time.time()}
            return data["value"][0]["id"]
            
        # Fallback: mailNickname (usualmente coincide con el username si es nube nativa)
        data = await self._request("GET", f"/users?$filter=mailNickname eq '{username}'&$select=id,userPrincipalName&$count=true", headers=headers)
        if data.get("value"):
            _user_id_cache[cache_key] = {"id": data["value"][0]["id"], "time": time.time()}
            return data["value"][0]["id"]
            
        # Fallback 2: userPrincipalName empiece con el username
        data = await self._request("GET", f"/users?$filter=startsWith(userPrincipalName,'{username}@')&$select=id,userPrincipalName&$count=true", headers=headers)
        if data.get("value"):
            _user_id_cache[cache_key] = {"id": data["value"][0]["id"], "time": time.time()}
            return data["value"][0]["id"]

        _user_id_cache[cache_key] = {"id": None, "time": time.time()}
        raise ValueError(f"No se encontró el usuario '{username}' en Microsoft Entra ID. Verifica la sincronización.")

    async def get_user_licenses(self, user_id: str) -> list:
        """Obtiene las licencias asignadas actualmente a un usuario por su ID"""
        try:
            data = await self._request("GET", f"/users/{user_id}?$select=assignedLicenses")
            return data.get("assignedLicenses", [])
        except Exception as e:
            raise ValueError(f"No se pudieron consultar las licencias del usuario: {e}")

    async def search_cloud_users(self, query: str = "*", limit: int = 50) -> list:
        """Busca usuarios en Entra ID por nombre, apellido, correo o userPrincipalName."""
        # Graph API no permite un $top mayor a 999
        if limit > 999:
            limit = 999
            
        if query == "*":
            endpoint = f"/users?$top={limit}&$select=id,displayName,userPrincipalName,mail,jobTitle,department,accountEnabled"
        else:
            q = query.replace("'", "''")
            endpoint = f"/users?$filter=startswith(displayName,'{q}') or startswith(userPrincipalName,'{q}') or startswith(mail,'{q}') or startswith(surname,'{q}') or startswith(givenName,'{q}')&$top={limit}&$select=id,displayName,userPrincipalName,mail,jobTitle,department,accountEnabled"
            
        try:
            headers = {"ConsistencyLevel": "eventual"}
            data = await self._request("GET", endpoint, headers=headers)
            results = []
            for user in data.get("value", []):
                results.append({
                    "id": user["id"],
                    "displayName": user.get("displayName", ""),
                    "userPrincipalName": user.get("userPrincipalName", ""),
                    "email": user.get("mail", "") or user.get("userPrincipalName", ""),
                    "jobTitle": user.get("jobTitle", ""),
                    "department": user.get("department", ""),
                    "enabled": user.get("accountEnabled", False),
                    "source": "Entra ID"
                })
            return results
        except Exception as e:
            print(f"[GraphService] Error buscando usuarios en la nube: {e}")
            return []

    async def assign_license(self, username: str, sku_id: str):
        """Asigna una licencia de Microsoft 365 a un usuario."""
        try:
            user_id = await self.resolve_user_id(username)
        except Exception as e:
            raise ValueError(str(e))

        endpoint = f"/users/{user_id}/assignLicense"
        payload = {
            "addLicenses": [
                {
                    "skuId": sku_id
                }
            ],
            "removeLicenses": []
        }
        result = await self._request("POST", endpoint, json=payload)
        
        # Bust the caches to reflect updated counts immediately
        global _subscribed_skus_cache, _license_summary_cache
        if self.tenant_id in _subscribed_skus_cache:
            _subscribed_skus_cache[self.tenant_id]["time"] = 0
        if self.tenant_id in _license_summary_cache:
            _license_summary_cache[self.tenant_id]["time"] = 0
        
        return result

    async def remove_license(self, username: str, sku_id: str):
        """Remueve una licencia específica de Microsoft 365 a un usuario."""
        try:
            user_id = await self.resolve_user_id(username)
        except Exception as e:
            raise ValueError(str(e))

        endpoint = f"/users/{user_id}/assignLicense"
        payload = {
            "addLicenses": [],
            "removeLicenses": [sku_id]
        }
        result = await self._request("POST", endpoint, json=payload)
        
        # Bust the caches to reflect updated counts immediately
        global _subscribed_skus_cache, _license_summary_cache
        if self.tenant_id in _subscribed_skus_cache:
            _subscribed_skus_cache[self.tenant_id]["time"] = 0
        if self.tenant_id in _license_summary_cache:
            _license_summary_cache[self.tenant_id]["time"] = 0
        
        return result

    async def remove_all_licenses(self, username: str):
        """Remueve todas las licencias asignadas al usuario."""
        try:
            user_id = await self.resolve_user_id(username)
            # Primero obtenemos las licencias actuales
            licenses = await self.get_user_licenses(username)
            if not licenses:
                return {"success": True, "message": "No tenía licencias asignadas"}
                
            sku_ids = [lic["skuId"] for lic in licenses]
            endpoint = f"/users/{user_id}/assignLicense"
            payload = {
                "addLicenses": [],
                "removeLicenses": sku_ids
            }
            await self._request("POST", endpoint, json=payload)
            return {"success": True, "message": f"Se removieron {len(sku_ids)} licencias."}
        except Exception as e:
            raise ValueError(str(e))

    async def get_user_licenses(self, username: str):
        """Obtiene las licencias asignadas actualmente a un usuario."""
        try:
            user_id = await self.resolve_user_id(username)
        except Exception as e:
            raise ValueError(str(e))
            
        data = await self._request("GET", f"/users/{user_id}/licenseDetails")
        return data.get("value", [])

    async def get_user_info_and_licenses(self, user_id: str):
        """Obtiene info básica de la cuenta y sus licencias para el diagnóstico."""
        # 1. Info básica
        try:
            user_data = await self._request("GET", f"/users/{user_id}?$select=accountEnabled,userPrincipalName")
        except Exception as e:
            user_data = {"accountEnabled": True} # Fallback
            
        # 2. Licencias
        try:
            lic_data = await self._request("GET", f"/users/{user_id}/licenseDetails")
            licenses = lic_data.get("value", [])
        except Exception as e:
            licenses = []
            
        return {
            "accountEnabled": user_data.get("accountEnabled", True),
            "licenses": licenses
        }

    async def get_all_users_license_summary(self):
        """Devuelve un diccionario {username_lower: bool} indicando si tienen licencias."""
        global _license_summary_cache
        cache = _license_summary_cache.setdefault(self.tenant_id, {"time": 0, "data": None})
        if time.time() - cache["time"] < _LICENSE_CACHE_TTL and cache["data"]:
            return cache["data"]

        token = await self._get_access_token()
        base_url = "https://graph.microsoft.com/v1.0"
        url = "/users?$select=onPremisesSamAccountName,mailNickname,assignedLicenses&$top=999"
        
        import httpx
        users_map = {}
        async with httpx.AsyncClient() as client:
            while url:
                req_url = url if url.startswith("http") else base_url + url
                h = {"Authorization": f"Bearer {token}", "ConsistencyLevel": "eventual"}
                res = await client.get(req_url, headers=h)
                if res.status_code >= 400:
                    break
                data = res.json()
                for u in data.get("value", []):
                    uname = u.get("onPremisesSamAccountName") or u.get("mailNickname")
                    if uname:
                        licenses = u.get("assignedLicenses", [])
                        users_map[uname.lower()] = len(licenses) > 0
                url = data.get("@odata.nextLink")
                
        cache["time"] = time.time()
        cache["data"] = users_map
        return users_map

    async def revoke_sessions(self, username: str):
        """Revoca todas las sesiones de Entra ID de un usuario."""
        try:
            user_id = await self.resolve_user_id(username)
        except Exception as e:
            raise ValueError(str(e))
            
        endpoint = f"/users/{user_id}/revokeSignInSessions"
        return await self._request("POST", endpoint)

    async def get_m365_groups(self):
        """Devuelve todos los grupos de Microsoft 365 y de Seguridad (solo cloud-native)."""
        endpoint = "/groups?$select=id,displayName,groupTypes,mailEnabled,securityEnabled,onPremisesSyncEnabled&$top=999"
        data = await self._request("GET", endpoint)
        groups = data.get("value", [])
        return [g for g in groups if not g.get("onPremisesSyncEnabled")]

    async def add_user_to_m365_group(self, username: str, group_id: str):
        """Añade un usuario a un grupo M365 usando $ref."""
        user_id = await self.resolve_user_id(username)
        endpoint = f"/groups/{group_id}/members/$ref"
        payload = {
            "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"
        }
        # Retorna 204 No Content en exito, así que request maneja eso
        try:
            await self._request("POST", endpoint, json=payload)
            return {"success": True}
        except Exception as e:
            if "already exist" in str(e).lower() or "one or more added object references already exist" in str(e).lower():
                return {"success": True, "message": "El usuario ya estaba en el grupo"}
            raise

    async def remove_user_from_m365_group(self, username: str, group_id: str):
        """Remueve un usuario de un grupo M365."""
        user_id = await self.resolve_user_id(username)
        endpoint = f"/groups/{group_id}/members/{user_id}/$ref"
        try:
            await self._request("DELETE", endpoint)
            return {"success": True}
        except Exception as e:
            # Si no existe ya, está ok
            if "Request_ResourceNotFound" in str(e):
                return {"success": True, "message": "El usuario no estaba en el grupo"}
            raise

    async def get_user_m365_groups(self, username: str):
        """Devuelve los grupos a los que pertenece el usuario (solo cloud-native)."""
        user_id = await self.resolve_user_id(username)
        endpoint = f"/users/{user_id}/memberOf?$select=id,displayName,groupTypes,onPremisesSyncEnabled"
        data = await self._request("GET", endpoint)
        groups = data.get("value", [])
        return [g for g in groups if not g.get("onPremisesSyncEnabled")]

    async def get_user_devices(self, username: str):
        """Devuelve los dispositivos registrados del usuario (Entra ID)."""
        user_id = await self.resolve_user_id(username)
        endpoint = f"/users/{user_id}/registeredDevices?$select=id,displayName,operatingSystem,isCompliant,approximateLastSignInDateTime"
        try:
            data = await self._request("GET", endpoint)
            return data.get("value", [])
        except Exception:
            return []

    async def get_mailbox_info(self, username: str):
        """Revisa si el usuario tiene un plan de Exchange habilitado y su uso real."""
        user_id = await self.resolve_user_id(username)
        endpoint = f"/users/{user_id}?$select=assignedPlans,userPrincipalName"
        try:
            data = await self._request("GET", endpoint)
            plans = data.get("assignedPlans", [])
            upn = data.get("userPrincipalName", "")
            exchange_plan = next((p for p in plans if p.get("service", "").lower() == "exchange" and p.get("capabilityStatus") == "Enabled"), None)
            
            if exchange_plan:
                res = {
                    "hasMailbox": True,
                    "service": "Exchange Online",
                    "status": "Habilitado"
                }
                
                # Intentar obtener el uso real a través de Reports API
                try:
                    token = await self._get_access_token()
                    report_url = "https://graph.microsoft.com/v1.0/reports/getMailboxUsageDetail(period='D7')"
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(report_url, headers={"Authorization": f"Bearer {token}"}, follow_redirects=False)
                        
                        csv_text = None
                        if resp.status_code == 302:
                            # Microsoft Graph devuelve un 302 a una URL de Azure Storage pre-autenticada
                            download_url = resp.headers.get("Location")
                            if download_url:
                                resp2 = await client.get(download_url) # SIN header de Auth
                                if resp2.status_code == 200:
                                    csv_text = resp2.text
                                else:
                                    res["report_error"] = f"Error descargando CSV: HTTP {resp2.status_code}"
                        elif resp.status_code == 200:
                            csv_text = resp.text
                        else:
                            res["report_error"] = f"Error HTTP {resp.status_code}: {resp.text}"
                            
                        if csv_text:
                            lines = csv_text.splitlines()
                            for line in lines[1:]:
                                cols = line.split(',')
                                # cols[1]: UPN, cols[8]: Storage Used (Byte), cols[9]: Issue Warning
                                if len(cols) > 10 and cols[1].lower() == upn.lower():
                                    res["storage_used"] = int(cols[8])
                                    res["issue_warning"] = int(cols[9])
                                    res["prohibit_send"] = int(cols[10])
                                    break
                except Exception as e:
                    res["report_error"] = str(e)

                return res
                
            return {"hasMailbox": False, "debug_data": plans}
        except Exception as e:
            print(f"Error mailbox: {e}")
            return {"hasMailbox": False, "error": str(e)}

    async def get_entra_user_status(self, username: str):
        """Obtiene el estado de sincronización y configuración en Entra ID."""
        user_id = await self.resolve_user_id(username)
        if not user_id:
            return {"success": False, "error": "Usuario no encontrado en Entra ID"}
            
        endpoint = f"/users/{user_id}?$select=onPremisesSyncEnabled,onPremisesLastSyncDateTime,mail,userPrincipalName,accountEnabled,id,proxyAddresses,signInActivity,onPremisesDistinguishedName,onPremisesImmutableId,onPremisesSamAccountName,onPremisesDomainName,onPremisesSecurityIdentifier"
        data = await self._request("GET", endpoint)
        
        if not data or "error" in data:
            return {"success": False, "error": data.get("error", "Error consultando Entra ID")}
            
        # Intentar obtener la IP desde auditLogs (requiere licencia P1/P2)
        ip_address = None
        try:
            audit_data = await self._request("GET", f"/auditLogs/signIns?$filter=userId eq '{user_id}'&$top=1")
            if audit_data and audit_data.get("value") and len(audit_data["value"]) > 0:
                ip_address = audit_data["value"][0].get("ipAddress")
        except Exception:
            pass # Si falla por permisos o licenciamiento, ignoramos
            
        sign_in_info = data.get("signInActivity", {})
        if ip_address:
            sign_in_info["ipAddress"] = ip_address
            
        return {
            "success": True,
            "data": {
                "id": data.get("id"),
                "accountEnabled": data.get("accountEnabled"),
                "mail": data.get("mail"),
                "userPrincipalName": data.get("userPrincipalName"),
                "onPremisesSyncEnabled": data.get("onPremisesSyncEnabled"),
                "onPremisesLastSyncDateTime": data.get("onPremisesLastSyncDateTime"),
                "onPremisesDistinguishedName": data.get("onPremisesDistinguishedName"),
                "onPremisesImmutableId": data.get("onPremisesImmutableId"),
                "onPremisesSamAccountName": data.get("onPremisesSamAccountName"),
                "onPremisesDomainName": data.get("onPremisesDomainName"),
                "onPremisesSecurityIdentifier": data.get("onPremisesSecurityIdentifier"),
                "proxyAddresses": data.get("proxyAddresses", []),
                "signInActivity": sign_in_info
            }
        }
    async def reset_user_mfa(self, username: str):
        """Borra todos los métodos de autenticación del usuario (MFA) excepto password.
        
        Microsoft Graph requiere endpoints específicos por tipo de método para DELETE.
        No se puede usar la ruta genérica /authentication/methods/{id}.
        """
        user_id = await self.resolve_user_id(username)
        
        # Mapeo de @odata.type a su endpoint específico de DELETE
        method_type_map = {
            "#microsoft.graph.phoneAuthenticationMethod": "phoneMethods",
            "#microsoft.graph.microsoftAuthenticatorMethod": "microsoftAuthenticatorMethods",
            "#microsoft.graph.softwareOathAuthenticationMethod": "softwareOathMethods",
            "#microsoft.graph.fido2AuthenticationMethod": "fido2Methods",
            "#microsoft.graph.emailAuthenticationMethod": "emailMethods",
            "#microsoft.graph.windowsHelloForBusinessAuthenticationMethod": "windowsHelloForBusinessMethods",
        }
        
        deleted_count = 0
        errors = []
        
        for odata_type, endpoint_segment in method_type_map.items():
            try:
                data = await self._request("GET", f"/users/{user_id}/authentication/{endpoint_segment}", api_version="beta")
                items = data.get("value", [])
                for item in items:
                    method_id = item.get("id")
                    try:
                        await self._request("DELETE", f"/users/{user_id}/authentication/{endpoint_segment}/{method_id}", api_version="beta")
                        deleted_count += 1
                    except Exception as e:
                        errors.append(f"{endpoint_segment}/{method_id}: {e}")
            except Exception:
                # El endpoint puede no existir o no tener métodos, continuar
                pass
        
        if errors and deleted_count == 0:
            raise ValueError(f"No se pudo eliminar ningún método: {'; '.join(errors)}")
        
        return {"success": True, "message": f"Se eliminaron {deleted_count} métodos de MFA. El usuario deberá re-registrarse.", "errors": errors if errors else None}

    async def offboard_user(self, username: str):
        """Desvinculación express (Macro-acción) en Entra ID."""
        user_id = await self.resolve_user_id(username)
        
        # 1. Cambiar contraseña por una aleatoria y deshabilitar cuenta
        import secrets
        import string
        new_password = "".join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*") for i in range(20))
        
        payload = {
            "accountEnabled": False,
            "passwordProfile": {
                "forceChangePasswordNextSignIn": True,
                "password": new_password
            }
        }
        
        try:
            await self._request("PATCH", f"/users/{user_id}", json=payload)
        except Exception as e:
            raise ValueError(f"Error deshabilitando cuenta o cambiando password: {e}")
            
        # 2. Revocar sesiones
        try:
            await self.revoke_sessions(username)
        except Exception as e:
            print(f"Advertencia: no se pudieron revocar las sesiones: {e}")
            
        # NOTA PARA EL FUTURO:
        # Aquí se podría ocultar de la GAL (showInAddressList=False)
        # y convertir el buzón a compartido si se interactúa con Exchange Online.
        
        return {"success": True, "message": "Cuenta deshabilitada, sesiones revocadas y contraseña reseteada."}

    async def get_user_mfa_status(self, username: str):
        """Obtiene el estado de MFA (Legacy) para el usuario consultando strongAuthenticationRequirements."""
        user_id = await self.resolve_user_id(username)
        endpoint = f"/users/{user_id}?$select=strongAuthenticationRequirements"
        try:
            data = await self._request("GET", endpoint, api_version="beta")
            reqs = data.get("strongAuthenticationRequirements", [])
            if not reqs:
                return {"success": True, "mfaState": "disabled"}
            # Verificar si hay estado Enforced o Enabled
            states = [r.get("state", "").lower() for r in reqs]
            if "enforced" in states or "enabled" in states:
                return {"success": True, "mfaState": "enabled"}
            return {"success": True, "mfaState": "disabled"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_user_mfa_status(self, username: str, enable: bool):
        """Habilita o deshabilita el MFA (Legacy) para el usuario mediante strongAuthenticationRequirements."""
        user_id = await self.resolve_user_id(username)
        endpoint = f"/users/{user_id}"
        payload = {
            "strongAuthenticationRequirements": [{"state": "Enforced"}] if enable else []
        }
        try:
            await self._request("PATCH", endpoint, api_version="beta", json=payload)
            return {"success": True, "message": f"MFA {'habilitado' if enable else 'deshabilitado'} exitosamente."}
        except Exception as e:
            raise ValueError(f"Error modificando el estado MFA: {e}")

    async def get_inactive_licensed_users(self, days_threshold: int = 90) -> list:
        """Encuentra usuarios con licencias y devuelve sus fechas de último inicio de sesión (AD y Outlook)."""
        import datetime
        now = datetime.datetime.utcnow()
        # Añadimos accountEnabled, onPremisesSamAccountName y onPremisesImmutableId al select
        endpoint = f"/users?$select=id,displayName,userPrincipalName,assignedLicenses,signInActivity,onPremisesSyncEnabled,accountEnabled,onPremisesSamAccountName,onPremisesImmutableId&$top=999"
        
        try:
            # Obtener TODOS los SKUs reales del tenant para que no quede nada excluido
            subscribed_skus = await self.get_subscribed_skus()
            target_sku_ids = {sku["skuId"] for sku in subscribed_skus}
            
            users_data = []
            
            fallback_mode = False
            
            # Loop de paginación para traer TODOS los usuarios
            while endpoint:
                # Si el endpoint viene de nextLink, limpiamos la base url para _request
                if endpoint.startswith("https://graph.microsoft.com/v1.0/"):
                    endpoint = endpoint.replace("https://graph.microsoft.com/v1.0/", "")
                    
                try:
                    data = await self._request("GET", endpoint)
                except ValueError as e:
                    if "Authentication_RequestFromNonPremiumTenantOrB2CTenant" in str(e) and not fallback_mode:
                        fallback_mode = True
                        print(f"[GraphService] Tenant sin licencia Premium. Reintentando sin signInActivity.")
                        endpoint = endpoint.replace(",signInActivity", "").replace("signInActivity,", "")
                        data = await self._request("GET", endpoint)
                    else:
                        raise e
                
                for user in data.get("value", []):
                    licenses = user.get("assignedLicenses", [])
                        
                    ad_sign_in = None
                    outlook_sign_in = None
                    
                    if "signInActivity" in user and user["signInActivity"]:
                        ad_sign_in_str = user["signInActivity"].get("lastSignInDateTime")
                        outlook_sign_in_str = user["signInActivity"].get("lastNonInteractiveSignInDateTime")
                        
                        if ad_sign_in_str:
                            ad_sign_in = ad_sign_in_str
                        if outlook_sign_in_str:
                            outlook_sign_in = outlook_sign_in_str
                    
                    def calc_days(date_str):
                        if not date_str:
                            return 9999
                        try:
                            # Parse ISO format string (e.g. 2023-01-01T00:00:00Z)
                            dt = datetime.datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
                            return max(0, (now - dt).days)
                        except Exception:
                            return 9999
                            
                    user_target_licenses = []
                    for lic in licenses:
                        # Buscamos el nombre de cualquier licencia que tenga, coincida o no
                        sku_part = next((s["skuPartNumber"] for s in subscribed_skus if s["skuId"] == lic.get("skuId")), "Desconocida")
                        user_target_licenses.append(sku_part)

                    users_data.append({
                        "id": user["id"],
                        "displayName": user.get("displayName", ""),
                        "userPrincipalName": user.get("userPrincipalName", ""),
                        "onPremisesSamAccountName": user.get("onPremisesSamAccountName", ""),
                        "onPremisesImmutableId": user.get("onPremisesImmutableId", ""),
                        "accountEnabled": user.get("accountEnabled", True),
                        "onPremisesSyncEnabled": user.get("onPremisesSyncEnabled", False),
                        "lastSignInDateTimeAd": ad_sign_in,
                        "lastSignInDateTimeOutlook": outlook_sign_in,
                        "daysInactiveAd": calc_days(ad_sign_in),
                        "daysInactiveOutlook": calc_days(outlook_sign_in),
                        "licensesCount": len(licenses),
                        "licenses": user_target_licenses
                    })
                
                endpoint = data.get("@odata.nextLink")
            
            return users_data
        except Exception as e:
            print(f"[GraphService] Error buscando licencias inactivas: {e}")
            raise ValueError(f"Error consultando Microsoft Graph: {str(e)}")

    async def transfer_onedrive(self, source_username: str, target_email: str):
        """Transfiere el control del OneDrive usando el endpoint de invite."""
        try:
            source_id = await self.resolve_user_id(source_username)
            endpoint = f"/users/{source_id}/drive/root/invite"
            payload = {
                "recipients": [{"email": target_email}],
                "requireSignIn": True,
                "sendSignInPromo": False,
                "roles": ["write"],
                "message": "Tienes acceso al OneDrive de este usuario offboarded."
            }
            # Esto devuelve los permisos creados
            result = await self._request("POST", endpoint, json=payload)
            return {"success": True, "data": result}
        except Exception as e:
            raise ValueError(f"Error transfiriendo OneDrive: {e}")

    async def generate_onedrive_master_link(self, source_username: str):
        """Genera un link mágico para el OneDrive."""
        try:
            source_id = await self.resolve_user_id(source_username)
            endpoint = f"/users/{source_id}/drive/root/createLink"
            payload = {
                "type": "edit",
                "scope": "organization"
            }
            result = await self._request("POST", endpoint, json=payload)
            link = result.get("link", {}).get("webUrl", "")
            return {"success": True, "link": link}
        except Exception as e:
            raise ValueError(f"Error generando link de OneDrive: {e}")

# --- Multitenant Support ---
_services_cache = {}

def get_graph_service(tenant_id: str = "1") -> MicrosoftGraphService:
    """Obtiene la instancia de Graph para el tenant seleccionado."""
    if not tenant_id:
        tenant_id = "1"
        
    if tenant_id in _services_cache:
        return _services_cache[tenant_id]
        
    if tenant_id == "1":
        svc = MicrosoftGraphService(
            tenant_id=env_settings.ENTRA_TENANT_ID,
            client_id=env_settings.ENTRA_CLIENT_ID,
            client_secret=env_settings.ENTRA_CLIENT_SECRET,
            tenant_name=getattr(env_settings, "ENTRA_TENANT_NAME", "Principal")
        )
        _services_cache["1"] = svc
        return svc
    elif tenant_id == "2":
        if not getattr(env_settings, "ENTRA_TENANT_ID_2", None):
            raise ValueError("El Tenant secundario (2) no está configurado en .env")
        svc = MicrosoftGraphService(
            tenant_id=env_settings.ENTRA_TENANT_ID_2,
            client_id=env_settings.ENTRA_CLIENT_ID_2,
            client_secret=env_settings.ENTRA_CLIENT_SECRET_2,
            tenant_name=getattr(env_settings, "ENTRA_TENANT_NAME_2", "Secundario")
        )
        _services_cache["2"] = svc
        return svc
    else:
        raise ValueError(f"Tenant index {tenant_id} no soportado.")

def get_available_tenants():
    """Retorna la lista de tenants configurados para el Frontend."""
    tenants = []
    if env_settings.ENTRA_TENANT_ID:
        tenants.append({"id": "1", "name": getattr(env_settings, "ENTRA_TENANT_NAME", "Principal")})
    if getattr(env_settings, "ENTRA_TENANT_ID_2", None):
        tenants.append({"id": "2", "name": getattr(env_settings, "ENTRA_TENANT_NAME_2", "Secundario")})
    return tenants

# Mantenemos graph_service apuntando al Tenant 1 para retrocompatibilidad
graph_service = get_graph_service("1")

import subprocess
import json
import tempfile
import os
import asyncio

async def check_exchange_setup():
    """Verifica si el entorno está listo para Exchange Online (Módulo y Certificado)."""
    ps_file_path = None
    try:
        ps_script = '''
        $ErrorActionPreference = "Stop"
        $module = Get-Module -ListAvailable -Name ExchangeOnlineManagement
        $cert = Get-ChildItem -Path Cert:\\CurrentUser\\My | Where-Object Subject -match "AdminDA-ExchangeOnline" | Select-Object -First 1
        
        $result = @{
            module_installed = [bool]$module
            cert_installed = [bool]$cert
            thumbprint = if ($cert) { $cert.Thumbprint } else { $null }
        }
        $result | ConvertTo-Json -Compress
        '''
        fd, ps_file_path = tempfile.mkstemp(suffix=".ps1")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(ps_script)
            
        def run_ps():
            return subprocess.run(
                ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps_file_path],
                capture_output=True,
                text=True
            )
            
        process = await asyncio.to_thread(run_ps)
        data = json.loads(process.stdout.strip())
        return data
    except Exception as e:
        import traceback
        with open("debug.txt", "a") as f:
            f.write(f"check_exchange_setup ERROR:\n{traceback.format_exc()}\n")
        return {"module_installed": False, "cert_installed": False, "thumbprint": None, "error": str(e)}
    finally:
        if ps_file_path and os.path.exists(ps_file_path):
            try:
                os.remove(ps_file_path)
            except:
                pass

async def setup_exchange():
    """Ejecuta la instalación del módulo y crea el certificado Self-Signed."""
    ps_file_path = None
    try:
        ps_script = '''
        $ErrorActionPreference = "Stop"
        # 1. Instalar el Módulo (Aceptando dependencias y sin confirmación)
        Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -ErrorAction SilentlyContinue | Out-Null
        Set-PSRepository -Name "PSGallery" -InstallationPolicy Trusted -ErrorAction SilentlyContinue | Out-Null
        Install-Module -Name ExchangeOnlineManagement -Force -AllowClobber -Scope CurrentUser

        # 2. Crear Certificado
        $cert = Get-ChildItem -Path Cert:\\CurrentUser\\My | Where-Object Subject -match "AdminDA-ExchangeOnline" | Select-Object -First 1
        if (-not $cert) {
            $cert = New-SelfSignedCertificate -Subject "CN=AdminDA-ExchangeOnline" `
                                              -CertStoreLocation "Cert:\\CurrentUser\\My" `
                                              -KeyExportPolicy Exportable `
                                              -KeySpec Signature `
                                              -KeyAlgorithm RSA `
                                              -KeyLength 2048 `
                                              -NotAfter (Get-Date).AddYears(2)
        }

        # 3. Exportar Certificado
        $desktopPath = [Environment]::GetFolderPath("Desktop")
        if (-not $desktopPath) { $desktopPath = "C:\\" }
        $cerPath = "$desktopPath\\AdminDA_Exchange.cer"
        Export-Certificate -Cert $cert -FilePath $cerPath -Force | Out-Null

        $result = @{
            success = $true
            thumbprint = $cert.Thumbprint
            cer_path = $cerPath
        }
        $result | ConvertTo-Json -Compress
        '''
        fd, ps_file_path = tempfile.mkstemp(suffix=".ps1")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(ps_script)
            
        def run_ps():
            return subprocess.run(
                ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps_file_path],
                capture_output=True,
                text=True
            )
            
        process = await asyncio.to_thread(run_ps)
        
        if process.returncode != 0:
            err_msg = process.stderr.strip()
            if not err_msg:
                err_msg = process.stdout.strip()
            raise ValueError(f"Error en Setup de Exchange: {err_msg}")
            
        out_str = process.stdout.strip()
        if not out_str:
            raise ValueError("El script no devolvió ningún resultado (stdout vacío).")
        return json.loads(out_str)
    except Exception as e:
        import traceback
        with open("debug.txt", "a") as f:
            f.write(f"setup_exchange ERROR:\n{traceback.format_exc()}\n")
        raise ValueError(f"{str(e)}")
    finally:
        if ps_file_path and os.path.exists(ps_file_path):
            try:
                os.remove(ps_file_path)
            except:
                pass

async def get_quarantined_emails_ps(
    recipient: str = None, 
    sender: str = None, 
    subject: str = None, 
    quarantine_type: str = None
):
    """Consulta correos en cuarentena usando Exchange Online PS con filtros dinámicos."""
    setup_status = await check_exchange_setup()
    thumbprint = setup_status.get("thumbprint")
    
    connect_cmd = ""
    if thumbprint:
        from app.core.config import env_settings
        client_id = env_settings.ENTRA_CLIENT_ID
        tenant_domain = "105code.cloud"
        connect_cmd = f'Connect-ExchangeOnline -CertificateThumbprint "{thumbprint}" -AppId "{client_id}" -Organization "{tenant_domain}" -ShowProgress $false -ErrorAction Stop'
        
    params = ["-PageSize 100"] 
    if recipient:
        params.append(f'-RecipientAddress "{recipient}"')
    if sender:
        params.append(f'-SenderAddress "{sender}"')
    if subject:
        params.append(f'-Subject "{subject}"')
    if quarantine_type and quarantine_type.lower() != "all":
        params.append(f'-QuarantineType {quarantine_type}')
        
    params_str = " ".join(params)
        
    ps_script = f'''
    try {{
        {connect_cmd}
        $messages = Get-QuarantineMessage {params_str} -ErrorAction Stop
        if (-not $messages) {{
            Write-Output "[]"
            exit 0
        }}
        $result = @()
        foreach ($msg in $messages) {{
            $result += [PSCustomObject]@{{
                Identity = $msg.Identity
                ReceivedTime = $msg.ReceivedTime.ToString("yyyy-MM-ddTHH:mm:ss")
                SenderAddress = $msg.SenderAddress
                RecipientAddress = ($msg.RecipientAddress -join ", ")
                Subject = $msg.Subject
                QuarantineTypes = ($msg.QuarantineTypes -join ", ")
                Expires = $msg.Expires.ToString("yyyy-MM-ddTHH:mm:ss")
            }}
        }}
        $result | ConvertTo-Json -Compress
    }} catch {{
        Write-Error $_.Exception.Message
        exit 1
    }}
    '''
    def run_ps():
        return subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', ps_script],
            capture_output=True,
            text=True
        )
        
    process = await asyncio.to_thread(run_ps)
    
    if process.returncode != 0:
        raise ValueError(f"Error PowerShell Exchange: {process.stderr.strip()}")
        
    out_str = process.stdout.strip()
    if not out_str or out_str == "[]":
        return []
        
    try:
        data = json.loads(out_str)
        if isinstance(data, dict):
            return [data]
        return data
    except json.JSONDecodeError:
        return []

async def release_quarantined_email_ps(message_identity: str):
    """Libera un correo de la cuarentena."""
    setup_status = await check_exchange_setup()
    thumbprint = setup_status.get("thumbprint")
    
    connect_cmd = ""
    if thumbprint:
        from app.core.config import env_settings
        client_id = env_settings.ENTRA_CLIENT_ID
        tenant_domain = "105code.cloud"
        connect_cmd = f'Connect-ExchangeOnline -CertificateThumbprint "{thumbprint}" -AppId "{client_id}" -Organization "{tenant_domain}" -ShowProgress $false -ErrorAction Stop'
        
    ps_script = f'''
    try {{
        {connect_cmd}
        Release-QuarantineMessage -Identity "{message_identity}" -ReleaseToAll -ErrorAction Stop
        Write-Output '{{"success": true}}'
    }} catch {{
        Write-Error $_.Exception.Message
        exit 1
    }}
    '''
    def run_ps():
        return subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', ps_script],
            capture_output=True,
            text=True
        )
        
    process = await asyncio.to_thread(run_ps)
    
    if process.returncode != 0:
        raise ValueError(f"Error al liberar correo: {process.stderr.strip()}")
        
    try:
        return json.loads(process.stdout.strip())
    except Exception as e:
        raise ValueError(f"Error procesando resultado: {str(e)}")
