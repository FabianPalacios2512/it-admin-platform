import httpx
import time
from app.core.config import env_settings

_license_summary_cache = {"time": 0, "data": None}
_subscribed_skus_cache = {"time": 0, "data": None}
_user_id_cache = {}
_LICENSE_CACHE_TTL = 300
_USER_CACHE_TTL = 3600

class MicrosoftGraphService:
    def __init__(self):
        self.tenant_id = env_settings.ENTRA_TENANT_ID
        self.client_id = env_settings.ENTRA_CLIENT_ID
        self.client_secret = env_settings.ENTRA_CLIENT_SECRET
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
        if time.time() - _subscribed_skus_cache["time"] < _LICENSE_CACHE_TTL and _subscribed_skus_cache["data"]:
            return _subscribed_skus_cache["data"]
            
        data = await self._request("GET", "/subscribedSkus")
        skus = data.get("value", [])
        
        _subscribed_skus_cache["data"] = skus
        _subscribed_skus_cache["time"] = time.time()
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
        """Encuentra el ID del usuario en Entra ID utilizando su username local."""
        username_lower = username.lower()
        if username_lower in _user_id_cache:
            if time.time() - _user_id_cache[username_lower]["time"] < _USER_CACHE_TTL:
                cached_id = _user_id_cache[username_lower]["id"]
                if not cached_id:
                    raise ValueError(f"No se encontró el usuario '{username}' en Microsoft Entra ID. Verifica la sincronización.")
                return cached_id
                
        headers = {"ConsistencyLevel": "eventual"}
        
        # Intentamos primero por onPremisesSamAccountName (si hay AD Connect)
        data = await self._request("GET", f"/users?$filter=onPremisesSamAccountName eq '{username}'&$select=id,userPrincipalName&$count=true", headers=headers)
        if data.get("value"):
            _user_id_cache[username_lower] = {"id": data["value"][0]["id"], "time": time.time()}
            return data["value"][0]["id"]
            
        # Fallback: mailNickname (usualmente coincide con el username si es nube nativa)
        data = await self._request("GET", f"/users?$filter=mailNickname eq '{username}'&$select=id,userPrincipalName&$count=true", headers=headers)
        if data.get("value"):
            _user_id_cache[username_lower] = {"id": data["value"][0]["id"], "time": time.time()}
            return data["value"][0]["id"]
            
        # Fallback 2: userPrincipalName empiece con el username
        data = await self._request("GET", f"/users?$filter=startsWith(userPrincipalName,'{username}@')&$select=id,userPrincipalName&$count=true", headers=headers)
        if data.get("value"):
            _user_id_cache[username_lower] = {"id": data["value"][0]["id"], "time": time.time()}
            return data["value"][0]["id"]

        _user_id_cache[username_lower] = {"id": None, "time": time.time()}
        raise ValueError(f"No se encontró el usuario '{username}' en Microsoft Entra ID. Verifica la sincronización.")

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
        return await self._request("POST", endpoint, json=payload)

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
        if time.time() - _license_summary_cache["time"] < _LICENSE_CACHE_TTL and _license_summary_cache["data"]:
            return _license_summary_cache["data"]

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
                
        _license_summary_cache["time"] = time.time()
        _license_summary_cache["data"] = users_map
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
            
        endpoint = f"/users/{user_id}?$select=onPremisesSyncEnabled,onPremisesLastSyncDateTime,mail,userPrincipalName,accountEnabled,id,proxyAddresses,signInActivity"
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

graph_service = MicrosoftGraphService()
