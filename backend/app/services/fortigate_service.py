import socket
import time
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import requests
import urllib3
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_AUDIT_CACHE: Dict[str, Dict[str, Any]] = {}
_AUDIT_LOCK = Lock()
_AUDIT_TTL_SECONDS = 12
_PLATFORM_HINT_CACHE: Dict[str, Any] = {}
_PLATFORM_HINT_TTL = 180

class FortigateService:
    def __init__(self, ip: str, token: str):
        self.ip = ip
        self.token = token
        self.base_url = f"https://{self.ip}/api/v2/monitor"
        
    # Perfiles de Traffic Shaper (per-ip-shaper) provisionados automáticamente en cada FortiGate
    # Límites viejos (Low-Priority, etc.) solo para leer filas ya creadas.
    SHAPER_PROFILES = [
        {"name": "NOC-Low-Priority", "label": "Low-Priority", "max_bandwidth_kbps": 1024, "max_sessions": 20},
        {"name": "NOC-Guest", "label": "Guest / Invitados", "max_bandwidth_kbps": 2048, "max_sessions": 15},
        {"name": "NOC-Standard", "label": "Standard", "max_bandwidth_kbps": 5120, "max_sessions": 0},
        {"name": "NOC-VIP", "label": "VIP / Alta Prioridad", "max_bandwidth_kbps": 20480, "max_sessions": 0},
    ]

    def _request(self, endpoint: str, params: Dict = None, method="GET", payload=None, is_cmdb=False, is_log=False, timeout=12, raise_on_error=False) -> Any:
        if is_cmdb:
            base = f"https://{self.ip}/api/v2/cmdb"
        elif is_log:
            base = f"https://{self.ip}/api/v2/log"
        else:
            base = self.base_url
        url = f"{base}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
        if params is None:
            params = {}
            
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, params=params, verify=False, timeout=timeout)
            elif method == "POST":
                resp = requests.post(url, headers=headers, params=params, json=payload, verify=False, timeout=timeout)
            elif method == "PUT":
                resp = requests.put(url, headers=headers, params=params, json=payload, verify=False, timeout=timeout)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, params=params, json=payload, verify=False, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", data)
        except Exception as e:
            print(f"FortiGate API Error ({url}): {e}")
            detail = ""
            if hasattr(e, 'response') and e.response is not None:
                print(e.response.text)
                detail = e.response.text
            if raise_on_error:
                raise Exception(f"FortiGate API Error en {endpoint}: {detail or e}")
            return []

    def reserve_dhcp(self, mac: str, ip_to_reserve: str, create_fw_address: bool):
        import ipaddress as ipaddr

        # 1. Obtener lista de servidores DHCP - endpoint correcto: system.dhcp
        servers = self._request("/system.dhcp/server", is_cmdb=True)
        if not servers or not isinstance(servers, list):
            raise Exception("No se encontraron servidores DHCP en el FortiGate.")
            
        # 2. Encontrar el servidor DHCP cuyo rango contiene la IP a reservar
        target_server_id = None
        try:
            target_ip = ipaddr.ip_address(ip_to_reserve)
        except ValueError:
            raise Exception(f"IP inválida: {ip_to_reserve}")

        for s in servers:
            for rng in s.get("ip-range", []):
                start = rng.get("start-ip")
                end = rng.get("end-ip")
                if not start or not end:
                    continue
                try:
                    if ipaddr.ip_address(start) <= target_ip <= ipaddr.ip_address(end):
                        target_server_id = s.get("id")
                        break
                except ValueError:
                    continue
            if target_server_id:
                break
        
        # Fallback: si la IP no está en ningún rango, buscar por interfaz/gateway
        if not target_server_id:
            for s in servers:
                gateway = s.get("default-gateway", "")
                netmask = s.get("netmask", "")
                if gateway and gateway != "0.0.0.0" and netmask and netmask != "0.0.0.0":
                    try:
                        net = ipaddr.IPv4Network(f"{gateway}/{netmask}", strict=False)
                        if target_ip in net:
                            target_server_id = s.get("id")
                            break
                    except ValueError:
                        continue
                        
        if not target_server_id:
            raise Exception(f"No se encontró servidor DHCP que maneje el rango de {ip_to_reserve}.")
            
        # 3. Hacer el POST para reservar
        # NOTA: No incluir 'type' en el payload - FortiOS lo rechaza con error -61
        payload = {
            "mac": mac,
            "ip": ip_to_reserve,
            "description": "Reserved via IT Admin Platform"
        }
        
        res = self._request(
            f"/system.dhcp/server/{target_server_id}/reserved-address",
            method="POST",
            payload=payload,
            is_cmdb=True
        )
        return res

    def revoke_dhcp(self, mac: str, server_id: int = None):
        """Elimina una reserva DHCP existente por MAC. Usa server_id si se conoce."""

        # 1. Si no conocemos el server_id, buscarlo en la lista de servidores
        if server_id is None:
            servers = self._request("/system.dhcp/server", is_cmdb=True)
            if not servers or not isinstance(servers, list):
                raise Exception("No se encontraron servidores DHCP en el FortiGate.")

            for s in servers:
                for res in s.get("reserved-address", []):
                    if res.get("mac", "").lower() == mac.lower():
                        server_id = s.get("id")
                        reservation_id = res.get("id")
                        break
                if server_id:
                    break
        else:
            # Buscar directamente en el servidor conocido
            server_data = self._request(f"/system.dhcp/server/{server_id}", is_cmdb=True)
            server = server_data[0] if isinstance(server_data, list) and server_data else {}
            reservation_id = None
            for res in server.get("reserved-address", []):
                if res.get("mac", "").lower() == mac.lower():
                    reservation_id = res.get("id")
                    break

        if not server_id or not reservation_id:
            raise Exception(f"No se encontró reserva activa para MAC {mac}.")

        result = self._request(
            f"/system.dhcp/server/{server_id}/reserved-address/{reservation_id}",
            method="DELETE",
            is_cmdb=True
        )
        return result

    @staticmethod
    def _normalize_mac(mac: str) -> str:
        hex_only = "".join(ch for ch in str(mac or "").lower() if ch in "0123456789abcdef")
        if len(hex_only) != 12:
            return ""
        return ":".join(hex_only[i:i + 2] for i in range(0, 12, 2))

    def resolve_isolate_target(self, ip: str = "", mac: str = "") -> Dict[str, str]:
        ip_n = str(ip or "").strip().split("/")[0]
        mac_n = self._normalize_mac(mac)
        leases = self._request("/system/dhcp", timeout=6)
        if not isinstance(leases, list):
            leases = []

        if mac_n:
            for lease in leases:
                if not isinstance(lease, dict):
                    continue
                if self._normalize_mac(lease.get("mac") or "") != mac_n:
                    continue
                return {
                    "ip": str(lease.get("ip") or ip_n).strip(),
                    "mac": mac_n,
                    "hostname": str(lease.get("hostname") or ""),
                }
            if not ip_n:
                raise Exception(
                    f"La MAC {mac_n} no tiene lease DHCP activo en este FortiGate. "
                    "Elige el equipo de la lista o indica la IP actual."
                )

        if ip_n:
            lease = next(
                (row for row in leases if isinstance(row, dict) and str(row.get("ip") or "") == ip_n),
                None,
            )
            return {
                "ip": ip_n,
                "mac": self._normalize_mac((lease or {}).get("mac") or mac_n),
                "hostname": str((lease or {}).get("hostname") or ""),
            }

        raise Exception("Indica un FortiGate, y luego un equipo de la lista, una IP o una MAC con lease activo.")

    def ban_ip(self, ip: str, expiry: int = 3600) -> Any:
        """Pone una IP en user/banned (blackhole). 0 = indefinido."""
        ip_n = str(ip or "").strip().split("/")[0]
        if not ip_n:
            raise Exception("IP inválida para cuarentena.")
        result = self._request(
            "/user/banned/add_users",
            method="POST",
            payload={"ip_addresses": [ip_n], "expiry": int(expiry)},
            timeout=10,
            raise_on_error=True,
        )
        banned = {row.get("ip") for row in self.list_banned()}
        if ip_n not in banned:
            raise Exception(
                f"FortiGate aceptó el ban pero {ip_n} no quedó en user/banned. "
                "Revisa el perfil API y que el tráfico de ese equipo pase por este firewall."
            )
        self._clear_sessions_from(ip_n)
        return result

    def unban_ip(self, ip: str) -> Any:
        """Saca una IP de la cuarentena y la vuelve a habilitar en red."""
        last_error = None
        for payload in (
            {"ip_addresses": [ip]},
            {"ip_addresses": [{"ip": ip}]},
            {"ip": ip},
        ):
            try:
                return self._request(
                    "/user/banned/clear_users",
                    method="POST",
                    payload=payload,
                    timeout=10,
                    raise_on_error=True,
                )
            except Exception as exc:
                last_error = exc
        raise last_error or Exception(f"No se pudo sacar {ip} de cuarentena.")

    def list_banned(self) -> List[Dict[str, Any]]:
        rows = self._as_list(self._request("/user/banned", timeout=10))
        out = []
        for row in rows:
            raw_ip = row.get("ip") or row.get("ip_address") or row.get("addr") or row.get("source") or ""
            if isinstance(raw_ip, dict):
                raw_ip = raw_ip.get("ip") or raw_ip.get("addr") or ""
            ip = str(raw_ip).split("/")[0].strip()
            if not ip:
                continue
            out.append({
                "ip": ip,
                "created": row.get("created") or row.get("created_timestamp") or 0,
                "expires": row.get("expires") or row.get("expiry") or row.get("expire") or 0,
                "hostname": row.get("hostname") or row.get("name") or "",
            })
        return out

    NOC_MAC_GROUP = "QuarantinedDevices"
    NOC_MAC_POLICY = "NOC-MAC-DENY"
    NOC_MAC_TARGET = "NOC-MAC"

    def _mac_addr_name(self, mac: str) -> str:
        return self._safe_object_name("NOC-MAC", self._normalize_mac(mac).replace(":", ""))

    def _mac_object_names(self) -> List[str]:
        names = []
        for row in self._as_list(self._request("/firewall/address", is_cmdb=True)):
            name = str(row.get("name") or "")
            if name.startswith("NOC-MAC-"):
                names.append(name)
        return names

    def _quarantine_cfg(self) -> Dict[str, Any]:
        raw = self._request("/user/quarantine", is_cmdb=True)
        return raw if isinstance(raw, dict) else {}

    def _quarantine_group_name(self) -> str:
        return str(self._quarantine_cfg().get("firewall-groups") or self.NOC_MAC_GROUP).strip() or self.NOC_MAC_GROUP

    def _addrgrp_exists(self, name: str) -> bool:
        if not name:
            return False
        groups = self._as_list(self._request("/firewall/addrgrp", is_cmdb=True))
        return any(str(row.get("name") or "") == name for row in groups)

    def _quarantine_mac(self, mac: str, reason: str = "") -> None:
        """Función nativa de FortiOS: config user quarantine / targets / macs drop enable."""
        self._request(
            "/user/quarantine",
            method="PUT",
            payload={"quarantine": "enable"},
            is_cmdb=True,
            raise_on_error=True,
        )
        note = (reason or f"Bloqueo MAC {mac}")[:63]
        mac_payload = {"mac": mac, "description": note, "drop": "enable"}
        targets = self._as_list(self._request("/user/quarantine/targets", is_cmdb=True))
        target = next((row for row in targets if str(row.get("entry") or "") == self.NOC_MAC_TARGET), None)
        if not target:
            self._request(
                "/user/quarantine/targets",
                method="POST",
                payload={"entry": self.NOC_MAC_TARGET, "description": "Bloqueo MAC NOC", "macs": [mac_payload]},
                is_cmdb=True,
                raise_on_error=True,
            )
            return
        already = any(self._normalize_mac(row.get("mac") if isinstance(row, dict) else row) == mac for row in (target.get("macs") or []))
        if already:
            self._request(
                f"/user/quarantine/targets/{self.NOC_MAC_TARGET}/macs/{mac}",
                method="PUT",
                payload={"description": note, "drop": "enable"},
                is_cmdb=True,
                raise_on_error=True,
            )
            return
        try:
            self._request(
                f"/user/quarantine/targets/{self.NOC_MAC_TARGET}/macs",
                method="POST",
                payload=mac_payload,
                is_cmdb=True,
                raise_on_error=True,
            )
        except Exception as exc:
            if "-5" not in str(exc) and "already" not in str(exc).lower():
                raise

    def _unquarantine_mac(self, mac: str) -> None:
        try:
            self._request(
                f"/user/quarantine/targets/{self.NOC_MAC_TARGET}/macs/{mac}",
                method="DELETE",
                is_cmdb=True,
                raise_on_error=True,
            )
        except Exception as exc:
            if "404" not in str(exc) and "-3" not in str(exc):
                print(f"NOC MAC: no se pudo borrar {mac} de user/quarantine ({exc})")

    def _clear_sessions_from(self, ip: str) -> int:
        """Cierra las sesiones vivas de esa IP. Sin esto el ping/navegador siguen hasta que expiren."""
        closed = 0
        for row in self.get_sessions(500):
            parsed = self._normalize_session(row) if row.get("saddr") or row.get("srcip") else row
            src = str(parsed.get("srcip") or "")
            if not src:
                src, _ = self._endpoint(row, "saddr", "srcip", "srcaddr", "source", "src")
            if src != ip:
                continue
            dst = str(parsed.get("dstip") or "")
            if not dst:
                dst, _ = self._endpoint(row, "daddr", "dstip", "dstaddr", "destination", "dst")
            proto = str(parsed.get("proto") or row.get("proto") or "tcp").lower()
            proto_map = {"tcp": "tcp", "udp": "udp", "icmp": "icmp", "6": "tcp", "17": "udp", "1": "icmp"}
            payload = {
                "pro": proto_map.get(proto, "tcp"),
                "saddr": ip,
                "daddr": dst,
                "sport": int(parsed.get("sport") or row.get("sport") or 0),
                "dport": int(parsed.get("dport") or row.get("dport") or 0),
            }
            if not payload["daddr"] or not payload["sport"] or not payload["dport"]:
                continue
            try:
                self._request("/firewall/session/close", method="POST", payload=payload, timeout=8, raise_on_error=True)
                closed += 1
            except Exception:
                continue
        return closed

    def _mac_deny_sources(self) -> List[str]:
        srcs = []
        group = self._quarantine_group_name()
        if self._addrgrp_exists(group):
            srcs.append(group)
        for row in self.list_mac_blocks():
            ip = str(row.get("current_ip") or row.get("ip") or "")
            if ip and ip.count(":") < 2:
                srcs.append(self._ensure_host_address_object(ip))
            elif row.get("mac"):
                lease_ip = self._ip_for_mac(row["mac"])
                if lease_ip:
                    srcs.append(self._ensure_host_address_object(lease_ip))
        return list(dict.fromkeys(srcs))

    def _ensure_mac_deny_policy(self, src_names: List[str]) -> Any:
        unique = list(dict.fromkeys([name for name in src_names if name]))
        if not unique:
            policies = self._as_list(self._request("/firewall/policy", is_cmdb=True))
            mine = next((row for row in policies if str(row.get("name") or "") == self.NOC_MAC_POLICY), None)
            if mine:
                self._delete_policy(self._shaping_policy_id(mine) or mine.get("policyid"))
            return None
        payload = self._deny_payload(
            self.NOC_MAC_POLICY,
            unique,
            ["all"],
            "Cuarentena MAC nativa (user quarantine). Debe ir antes de las políticas de allow.",
        )
        policies = self._as_list(self._request("/firewall/policy", is_cmdb=True))
        mine = next((row for row in policies if str(row.get("name") or "") == self.NOC_MAC_POLICY), None)
        if mine:
            policy_id = self._shaping_policy_id(mine) or mine.get("policyid")
            self._request(
                f"/firewall/policy/{policy_id}",
                method="PUT",
                payload=payload,
                is_cmdb=True,
                raise_on_error=True,
            )
        else:
            result = self._request("/firewall/policy", method="POST", payload=payload, is_cmdb=True, raise_on_error=True)
            policy_id = result.get("mkey") or result.get("policyid") if isinstance(result, dict) else None
            if not policy_id:
                policies = self._as_list(self._request("/firewall/policy", is_cmdb=True))
                mine = next((row for row in policies if str(row.get("name") or "") == self.NOC_MAC_POLICY), None)
                policy_id = self._shaping_policy_id(mine) if mine else None
        policies = self._as_list(self._request("/firewall/policy", is_cmdb=True))
        self._move_policy_before_first_accept(policy_id, policies)
        return policy_id

    def _mac_from_address_row(self, row: Dict[str, Any], name: str = "") -> str:
        macs = row.get("macaddr") or []
        mac = ""
        if isinstance(macs, list) and macs:
            first = macs[0]
            mac = first.get("macaddr") or first.get("mac") if isinstance(first, dict) else str(first or "")
        elif isinstance(macs, str):
            mac = macs
        return self._normalize_mac(mac or row.get("start-mac") or name)

    def _remove_address_from_groups(self, addr_name: str) -> None:
        for group in self._as_list(self._request("/firewall/addrgrp", is_cmdb=True)):
            members = []
            found = False
            for member in group.get("member") or []:
                name = member.get("name") if isinstance(member, dict) else str(member or "")
                if name == addr_name:
                    found = True
                    continue
                if name:
                    members.append(name)
            if not found:
                continue
            gname = str(group.get("name") or "")
            if members:
                self._ensure_address_group(gname, members, str(group.get("comment") or ""))
                continue
            self._remove_name_from_policies(gname)
            self._request(f"/firewall/addrgrp/{gname}", method="DELETE", is_cmdb=True, raise_on_error=True)

    def _remove_name_from_policies(self, addr_name: str) -> None:
        for policy in self._as_list(self._request("/firewall/policy", is_cmdb=True)):
            src = self._policy_member_names(policy, "srcaddr")
            dst = self._policy_member_names(policy, "dstaddr")
            if addr_name not in src and addr_name not in dst:
                continue
            src = [name for name in src if name != addr_name]
            dst = [name for name in dst if name != addr_name]
            pid = self._shaping_policy_id(policy) or policy.get("policyid")
            if not src or not dst:
                self._delete_policy(pid)
                continue
            self._request(
                f"/firewall/policy/{pid}",
                method="PUT",
                payload={
                    "srcaddr": [{"name": name} for name in src],
                    "dstaddr": [{"name": name} for name in dst],
                },
                is_cmdb=True,
                raise_on_error=True,
            )

    def ban_mac(self, mac: str, reason: str = "", ip: str = "") -> Dict[str, Any]:
        mac_n = self._normalize_mac(mac)
        if not mac_n:
            raise Exception("MAC inválida. Usa el formato AA:BB:CC:DD:EE:FF.")
        current_ip = str(ip or "").strip() or self._ip_for_mac(mac_n)
        if not current_ip:
            raise Exception(
                f"La MAC {mac_n} no tiene IP activa en este FortiGate. "
                "Elige el equipo de la lista para cortar ping y navegación de inmediato."
            )
        self._quarantine_mac(mac_n, f"{current_ip} {reason or 'Bloqueo MAC'}".strip())
        still = [row.get("mac") for row in self.list_mac_blocks()]
        if mac_n not in still:
            raise Exception(f"FortiOS no guardó {mac_n} en user/quarantine. El perfil API no puede escribir cuarentena.")
        self.ban_ip(current_ip, 0)
        try:
            srcs = self._mac_deny_sources()
            srcs.append(self._ensure_host_address_object(current_ip))
            self._ensure_mac_deny_policy(srcs)
        except Exception as exc:
            print(f"NOC MAC: política deny no quedó ({exc}). La MAC está en user/quarantine y {current_ip} en user/banned.")
        return {
            "mac": mac_n,
            "ip": current_ip,
            "group": self._quarantine_group_name(),
            "target": self.NOC_MAC_TARGET,
        }

    def list_mac_blocks(self) -> List[Dict[str, Any]]:
        out = []
        seen = set()
        cfg = self._quarantine_cfg()
        targets = cfg.get("targets") if isinstance(cfg.get("targets"), list) else []
        if not targets:
            targets = self._as_list(self._request("/user/quarantine/targets", is_cmdb=True))
        for target in targets:
            for mac_row in target.get("macs") or []:
                mac = self._normalize_mac(mac_row.get("mac") if isinstance(mac_row, dict) else mac_row)
                if not mac or mac in seen:
                    continue
                seen.add(mac)
                note = ""
                if isinstance(mac_row, dict):
                    note = str(mac_row.get("description") or "")
                described_ip = next((part for part in note.split() if part.count(".") == 3), "")
                lease_ip = described_ip or self._ip_for_mac(mac)
                display = note[len(described_ip):].strip() if described_ip and note.startswith(described_ip) else note
                out.append({
                    "ip": lease_ip or mac,
                    "current_ip": lease_ip,
                    "mac": mac,
                    "hostname": display or str(target.get("entry") or "NOC-MAC"),
                    "reason": display or "Bloqueo MAC",
                    "expires": 0,
                    "kind": "mac",
                })
        for row in self._as_list(self._request("/firewall/address", is_cmdb=True)):
            name = str(row.get("name") or "")
            if not name.startswith("NOC-MAC-"):
                continue
            mac = self._mac_from_address_row(row, name)
            if not mac or mac in seen:
                continue
            seen.add(mac)
            out.append({
                "ip": mac,
                "current_ip": self._ip_for_mac(mac),
                "mac": mac,
                "hostname": name,
                "reason": row.get("comment") or "Bloqueo MAC",
                "expires": 0,
                "kind": "mac",
            })
        return out

    def unban_mac(self, mac: str) -> Dict[str, Any]:
        raw = str(mac or "").strip()
        mac_n = self._normalize_mac(raw)
        if not mac_n and raw.startswith("NOC-MAC-"):
            mac_n = self._normalize_mac("".join(ch for ch in raw.lower() if ch in "0123456789abcdef"))
        current_ip = self._ip_for_mac(mac_n)
        if mac_n:
            self._unquarantine_mac(mac_n)
        if current_ip:
            try:
                self.unban_ip(current_ip)
            except Exception:
                pass
        addr_name = self._mac_addr_name(mac_n) if mac_n else raw
        try:
            self._remove_address_from_groups(addr_name)
            self._remove_name_from_policies(addr_name)
            self._request(f"/firewall/address/{addr_name}", method="DELETE", is_cmdb=True, raise_on_error=True)
        except Exception:
            pass
        remaining = self._mac_deny_sources() if self.list_mac_blocks() else []
        if current_ip:
            remaining = [name for name in remaining if name != f"NOC-HOST-{current_ip}"]
        self._ensure_mac_deny_policy(remaining)
        return {"mac": mac_n or raw, "ip": current_ip}

    def _ip_for_mac(self, mac: str) -> str:
        try:
            return str(self.resolve_isolate_target(mac=mac).get("ip") or "")
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # God Mode: acciones tácticas de respuesta activa (NOC/SOC)
    # ------------------------------------------------------------------

    def kill_session(self, srcip: str, dstip: str, proto: str = "tcp", sport: int = 0, dport: int = 0) -> Any:
        """Termina una sesión TCP/UDP activa en el FortiGate.

        Usa el endpoint Monitor API `/firewall/session/close`, que requiere una
        coincidencia exacta de protocolo/IPs/puertos. Si no nos pasan los puertos
        (por ejemplo, viene de una fila agregada de FortiView), intentamos resolverlos
        primero contra la tabla de sesiones activas.
        """
        proto_map = {"tcp": "tcp", "udp": "udp", "icmp": "icmp", "6": "tcp", "17": "udp", "1": "icmp"}
        pro = proto_map.get(str(proto).lower(), "tcp")

        target_sport, target_dport = sport, dport
        if not target_sport or not target_dport:
            for row in self.get_sessions(500):
                s_ip, s_port = self._endpoint(row, "srcip", "srcaddr", "source", "src", "saddr")
                d_ip, d_port = self._endpoint(row, "dstip", "dstaddr", "destination", "dst", "daddr")
                if s_ip == srcip and d_ip == dstip:
                    target_sport = target_sport or row.get("sport") or s_port
                    target_dport = target_dport or row.get("dport") or d_port
                    break

        if not target_sport or not target_dport:
            raise Exception(
                f"No se encontró la sesión activa {srcip} → {dstip} en la tabla de sesiones. "
                "Puede que ya haya expirado por sí sola."
            )

        payload = {"pro": pro, "saddr": srcip, "daddr": dstip, "sport": int(target_sport), "dport": int(target_dport)}
        return self._request("/firewall/session/close", method="POST", payload=payload, timeout=10, raise_on_error=True)

    def ensure_shaper_profile(self, profile: Dict[str, Any]) -> None:
        """Crea (o actualiza) un per-ip-shaper. FortiOS 8 usa firewall.shaper; 7 usa firewall/shaper."""
        payload = {
            "name": profile["name"],
            "bandwidth-unit": "kbps",
            "max-bandwidth": profile["max_bandwidth_kbps"],
            "max-concurrent-session": profile.get("max_sessions", 0),
        }
        last_error = None
        for base in ("/firewall.shaper/per-ip-shaper", "/firewall/shaper/per-ip-shaper"):
            try:
                rows = self._as_list(self._request(base, is_cmdb=True))
                exists = any(str(row.get("name") or "") == profile["name"] for row in rows)
                if exists:
                    self._request(
                        f"{base}/{profile['name']}",
                        method="PUT",
                        payload=payload,
                        is_cmdb=True,
                        raise_on_error=True,
                    )
                else:
                    try:
                        self._request(base, method="POST", payload=payload, is_cmdb=True, raise_on_error=True)
                    except Exception as exc:
                        if "-5" not in str(exc) and "already" not in str(exc).lower():
                            raise
                        self._request(
                            f"{base}/{profile['name']}",
                            method="PUT",
                            payload=payload,
                            is_cmdb=True,
                            raise_on_error=True,
                        )
                self._per_ip_shaper_base = base
                return
            except Exception as exc:
                last_error = exc
        raise Exception(f"No se pudo crear el perfil {profile['name']} en el FortiGate: {last_error}")

    def _profile_for_limit(self, shaper_name: str = "", max_mbps: Any = None) -> Dict[str, Any]:
        if max_mbps not in (None, "", 0, "0"):
            mbps = int(float(max_mbps))
            if mbps < 1:
                raise Exception("0 Mbps no es un tope. Si quieres dejarlo libre, quita el límite.")
            mbps = min(mbps, 10000)
            return {
                "name": f"NOC-LIMIT-{mbps}M",
                "label": f"{mbps} Mbps",
                "max_bandwidth_kbps": mbps * 1000,
                "max_sessions": 0,
            }
        name = str(shaper_name or "").replace("-pipe", "")
        match = re.match(r"NOC-LIMIT-(\d+)M$", name)
        if match:
            mbps = int(match.group(1))
            return {
                "name": f"NOC-LIMIT-{mbps}M",
                "label": f"{mbps} Mbps",
                "max_bandwidth_kbps": mbps * 1000,
                "max_sessions": 0,
            }
        profile = next((row for row in self.SHAPER_PROFILES if row["name"] == name), None)
        if profile:
            return profile
        raise Exception("Indica cuántos Mbps quieres limitar.")

    def _mbps_of_shaper(self, shaper_name: str) -> tuple:
        name = str(shaper_name or "").replace("-pipe", "")
        try:
            profile = self._profile_for_limit(name)
            mbps = profile["max_bandwidth_kbps"] / 1000
            if abs(mbps - round(mbps)) < 0.05:
                mbps = int(round(mbps))
            else:
                mbps = round(mbps, 2)
            return mbps, profile["label"]
        except Exception:
            return 0, name

    def _ensure_named_shaper(self, shaper_name: str = "", max_mbps: Any = None) -> str:
        profile = self._profile_for_limit(shaper_name, max_mbps)
        self.ensure_shaper_profile(profile)
        return profile["name"]

    def _ensure_shared_pipe(self, shaper_name: str) -> str:
        """Pipe compartido: el per-ip solo no corta la BAJADA. Forti usa traffic-shaper-reverse para el download."""
        profile = self._profile_for_limit(shaper_name)
        pipe_name = f"{profile['name']}-pipe"
        payload = {
            "name": pipe_name,
            "bandwidth-unit": "kbps",
            "guaranteed-bandwidth": 0,
            "maximum-bandwidth": profile["max_bandwidth_kbps"],
            "per-policy": "enable",
        }
        last_error = None
        for base in ("/firewall.shaper/traffic-shaper", "/firewall/shaper/traffic-shaper"):
            try:
                rows = self._as_list(self._request(base, is_cmdb=True))
                exists = any(str(row.get("name") or "") == pipe_name for row in rows)
                if exists:
                    self._request(f"{base}/{pipe_name}", method="PUT", payload=payload, is_cmdb=True, raise_on_error=True)
                else:
                    try:
                        self._request(base, method="POST", payload=payload, is_cmdb=True, raise_on_error=True)
                    except Exception as exc:
                        if "-5" not in str(exc) and "already" not in str(exc).lower():
                            raise
                        self._request(f"{base}/{pipe_name}", method="PUT", payload=payload, is_cmdb=True, raise_on_error=True)
                return pipe_name
            except Exception as exc:
                last_error = exc
        raise Exception(f"No se pudo crear el pipe {pipe_name}: {last_error}")

    def _shaping_policy_id(self, row: Optional[Dict[str, Any]]) -> Any:
        if not row:
            return None
        return row.get("id") if row.get("id") not in (None, 0, "0") else row.get("policyid")

    def _shaping_intfs(self, srcintf: str = "", dstintf: str = "") -> tuple:
        if srcintf and dstintf and srcintf.lower() != "any" and dstintf.lower() != "any":
            return [{"name": srcintf}], [{"name": dstintf}]
        policies = self._as_list(self._request("/firewall/policy", is_cmdb=True))
        accept = next((p for p in policies if str(p.get("action")) == "accept" and str(p.get("status") or "enable") != "disable"), None)
        if accept:
            src = [m for m in (accept.get("srcintf") or []) if isinstance(m, dict) and m.get("name")]
            dst = [m for m in (accept.get("dstintf") or []) if isinstance(m, dict) and m.get("name")]
            if src and dst:
                return src, dst
        return [{"name": "any"}], [{"name": "any"}]

    def _shaping_payload(
        self,
        name: str,
        comment: str,
        src_names: List[str],
        dest_names: List[str],
        shaper_name: str,
        srcintf: str = "",
        dstintf: str = "",
        direction: str = "symmetric",
    ) -> Dict[str, Any]:
        pipe = self._ensure_shared_pipe(shaper_name)
        src_if, dst_if = self._shaping_intfs(srcintf, dstintf)
        seen = set()
        dests = []
        for item in dest_names:
            if item and item not in seen:
                seen.add(item)
                dests.append({"name": item})
        rx_only = str(direction or "symmetric").lower() == "rx"
        return {
            "name": name,
            "comment": comment,
            "status": "enable",
            "ip-version": "4",
            "schedule": "always",
            "service": [{"name": "ALL"}],
            "srcaddr": [{"name": n} for n in src_names if n],
            "dstaddr": dests or [{"name": "all"}],
            "srcintf": src_if,
            "dstintf": dst_if,
            "per-ip-shaper": "" if rx_only else shaper_name,
            "traffic-shaper": "" if rx_only else pipe,
            "traffic-shaper-reverse": pipe,
        }

    def list_shaper_profiles(self) -> List[Dict[str, Any]]:
        """Lista shapers que ya existen. No crea perfiles Guest/VIP por defecto."""
        rows = self._as_list(self._request("/firewall.shaper/per-ip-shaper", is_cmdb=True))
        if not rows:
            rows = self._as_list(self._request("/firewall/shaper/per-ip-shaper", is_cmdb=True))
        for row in rows:
            mbps, label = self._mbps_of_shaper(row.get("name") or "")
            row["label"] = label
            row["mbps"] = mbps
        return rows

    def _safe_object_name(self, prefix: str, *parts: str) -> str:
        raw = "-".join(str(p or "").replace(".", "-").replace("*", "w").replace("/", "-") for p in parts)
        raw = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in raw)
        return f"{prefix}-{raw}"[:35].rstrip("-")

    def _address_name_if_exists(self, name: str = "", subnet: str = "", fqdn: str = "") -> str:
        rows = self._as_list(self._request("/firewall/address", is_cmdb=True))
        for row in rows:
            if name and row.get("name") == name:
                return name
            if fqdn and str(row.get("fqdn") or "").lower() == fqdn.lower():
                return row.get("name") or ""
            if subnet and str(row.get("subnet") or "").startswith(subnet.split()[0]):
                return row.get("name") or ""
        return ""

    def _create_mac_address(self, name: str, mac: str, comment: str = "") -> str:
        note = (comment or f"Bloqueo MAC {mac}")[:255]
        payloads = [
            {"name": name, "type": "mac", "macaddr": [{"macaddr": mac}], "comment": note},
            {"name": name, "type": "mac", "start-mac": mac, "end-mac": mac, "comment": note},
            {"name": name, "type": "mac", "macaddr": mac, "comment": note},
        ]
        existing = self._address_name_if_exists(name=name)
        last_error = None
        for payload in payloads:
            try:
                if existing:
                    self._request(f"/firewall/address/{name}", method="PUT", payload=payload, is_cmdb=True, raise_on_error=True)
                else:
                    self._request("/firewall/address", method="POST", payload=payload, is_cmdb=True, raise_on_error=True)
                return name
            except Exception as exc:
                last_error = exc
                if "-5" in str(exc) or "already" in str(exc).lower():
                    return name
        raise last_error or Exception(f"No se pudo crear el objeto MAC {mac}.")

    def _create_address(self, payload: Dict[str, Any]) -> str:
        name = payload["name"]
        existing = self._address_name_if_exists(
            name=name,
            subnet=str(payload.get("subnet") or ""),
            fqdn=str(payload.get("fqdn") or ""),
        )
        if existing:
            return existing
        try:
            self._request("/firewall/address", method="POST", payload=payload, is_cmdb=True, raise_on_error=True)
            return name
        except Exception as exc:
            # FortiOS 8 error -5 = el objeto ya existe; no volver a fallar.
            if "-5" in str(exc) or "already" in str(exc).lower():
                found = self._address_name_if_exists(
                    name=name,
                    subnet=str(payload.get("subnet") or ""),
                    fqdn=str(payload.get("fqdn") or ""),
                )
                if found:
                    return found
            raise

    def _ensure_host_address_object(self, ip: str) -> str:
        """Crea (si no existe) un objeto de dirección /32 para una IP puntual y devuelve su nombre."""
        return self._create_address({
            "name": f"NOC-HOST-{ip}",
            "type": "ipmask",
            "subnet": f"{ip} 255.255.255.255",
            "comment": "Creado automáticamente por IT Admin Platform (NOC/SOC)",
        })

    # Servicios "multi-dominio": el sitio principal es solo la puerta de entrada,
    # el video/contenido real viaja por dominios de CDN dedicados y distintos.
    # Bloquear solo el dominio visitado NO corta el streaming (ese fue el bug
    # reportado con Twitch/YouTube: "me reconoce como 3 IPs, 3 servicios").
    SERVICE_BUNDLES = (
        (("twitch.", "ttvnw.", "jtvnw.", "justin.tv"), "Twitch", ("twitch.tv", "ttvnw.net", "jtvnw.net")),
        (("youtube.", "youtu.be", "googlevideo.", "ytimg.", "ggpht."), "YouTube",
         ("youtube.com", "youtu.be", "googlevideo.com", "ytimg.com", "ggpht.com")),
        (("netflix.", "nflxvideo.", "nflximg.", "nflxext."), "Netflix",
         ("netflix.com", "nflxvideo.net", "nflximg.net", "nflxext.com")),
        (("facebook.", "fbcdn.", "fb.com", "fb.watch"), "Facebook", ("facebook.com", "fbcdn.net", "fb.watch")),
        (("instagram.", "cdninstagram."), "Instagram", ("instagram.com", "cdninstagram.com")),
        (("tiktok.", "tiktokcdn.", "tiktokv.", "musical.ly", "muscdn."), "TikTok",
         ("tiktok.com", "tiktokcdn.com", "tiktokv.com", "muscdn.com")),
        (("spotify.", "spotifycdn.", "scdn.co", "pscdn.co", "spoti.fi"), "Spotify",
         ("spotify.com", "spotifycdn.com", "scdn.co", "pscdn.co")),
        (("shopify.", "shopifycdn.", "myshopify.", "shopifysvc."), "Shopify",
         ("shopify.com", "shopifycdn.com", "myshopify.com")),
        (("office.com", "office.net", "microsoftonline.", "live.com"), "Microsoft 365", ("office.com", "office.net")),
    )
    # Plataformas donde vive una página: hogarymoda.com no se llama shopify,
    # pero al abrirla carga extensions.shopifycdn.com. No es "la misma hora":
    # es la infra que esa URL usa. GTM/Bing/MSN no entran aquí.
    PLATFORM_BUNDLES = (
        (("shopify.", "shopifycdn.", "myshopify.", "shopifysvc.", "shopifycloud."), "Shopify",
         ("shopify.com", "shopifycdn.com", "myshopify.com")),
        (("wix.com", "wixstatic.", "wixsite."), "Wix", ("wix.com", "wixstatic.com")),
        (("squarespace.", "sqsp.net", "squarespace-cdn."), "Squarespace", ("squarespace.com", "sqsp.net")),
        (("wordpress.com", "wp.com"), "WordPress", ("wordpress.com", "wp.com")),
    )
    # Sufijos de 2 partes donde el "dominio raíz" real necesita 3 niveles (empresa.com.co, etc.)
    _MULTI_PART_SUFFIXES = {
        "co.uk", "com.co", "com.mx", "com.br", "com.ar", "net.co", "org.co",
        "gov.co", "edu.co", "com.au", "co.in", "com.pe", "com.ec", "com.ve",
    }
    # Palabras que se repiten en casi cualquier destino: nunca son "la marca" de un servicio.
    _GENERIC_LABELS = {
        "www", "com", "net", "org", "io", "co", "uk", "tv", "info", "biz",
        "app", "apps", "cdn", "api", "static", "media", "m", "mobile", "s",
        "edge", "cloud", "akamai", "fastly", "cloudfront", "amazonaws",
        "azureedge", "msecnd", "google", "gstatic", "googleapis",
        "apple", "icloud", "microsoft", "office", "live", "outlook",
        "windows", "azure", "amazon", "aws", "gcp", "ak", "img", "image",
        "images", "assets", "web", "www2", "dev", "prod", "stage",
    }
    _GENERIC_ROOTS = {
        "akamaized.net", "edgesuite.net", "edgekey.net", "akamaihd.net",
        "googleusercontent.com", "gvt1.com", "gvt2.com", "gvt3.com",
        "doubleclick.net", "googlesyndication.com",
    }
    _BRAND_AFFIXES = (
        "images", "static", "assets", "media", "cache", "content",
        "download", "stream", "video", "files", "edge", "live",
        "cdn", "api", "app", "web", "img", "vod", "ak", "dl",
    )
    _SKIP_HOST_SUFFIXES = (".local", ".lan", ".internal", ".arpa", ".localhost")
    _BRAND_LABELS = {
        "spotify": "Spotify",
        "ivoox": "iVoox",
        "youtube": "YouTube",
        "twitch": "Twitch",
        "netflix": "Netflix",
        "facebook": "Facebook",
        "instagram": "Instagram",
        "tiktok": "TikTok",
    }

    def _root_domain(self, host: str) -> str:
        parts = host.split(".")
        if len(parts) <= 2:
            return host
        last_two = ".".join(parts[-2:])
        if last_two in self._MULTI_PART_SUFFIXES and len(parts) >= 3:
            return ".".join(parts[-3:])
        return last_two

    def _service_bundle_for_host(self, host: str) -> Optional[tuple]:
        for needles, label, domains in self.SERVICE_BUNDLES:
            if any(n in host for n in needles):
                return label, domains
        return None

    def _platform_bundle_for_host(self, host: str) -> Optional[tuple]:
        for needles, label, domains in self.PLATFORM_BUNDLES:
            if any(n in host for n in needles):
                return label, domains
        return None

    def _detect_site_platforms(self, host: str) -> List[tuple]:
        """Mira si esa URL vive en Shopify/Wix/etc. (cabeceras/HTML), no el tráfico de al lado."""
        cleaned = self._clean_domain(host)
        if not cleaned or self._service_bundle_for_host(cleaned):
            return []
        root = self._root_domain(cleaned)
        now = time.time()
        cached = _PLATFORM_HINT_CACHE.get(root)
        if cached and now - cached[0] < _PLATFORM_HINT_TTL:
            return list(cached[1])

        found: List[tuple] = []
        seen: Set[str] = set()

        def add(bundle: Optional[tuple]):
            if bundle and bundle[0] not in seen:
                seen.add(bundle[0])
                found.append(bundle)

        add(self._platform_bundle_for_host(cleaned))
        blob = ""
        try:
            resp = requests.get(
                f"https://{root}",
                timeout=5,
                verify=False,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            header_blob = " ".join(f"{k} {v}" for k, v in (resp.headers or {}).items())
            blob = f"{header_blob} {(resp.text or '')[:16000]}".lower()
        except Exception as exc:
            print(f"NOC: no se pudo leer {root} para detectar plataforma: {exc}")

        if blob:
            if "shopify" in blob or "shopifycdn" in blob or "myshopify" in blob:
                add(self._platform_bundle_for_host("shopifycdn.com"))
            if "wixstatic" in blob or "wix.com" in blob:
                add(self._platform_bundle_for_host("wixstatic.com"))
            if "squarespace" in blob or "sqsp.net" in blob:
                add(self._platform_bundle_for_host("squarespace.com"))
            if "wp.com" in blob and "wordpress" in blob:
                add(self._platform_bundle_for_host("wordpress.com"))

        _PLATFORM_HINT_CACHE[root] = (now, list(found))
        return found

    def _is_generic_root(self, root: str) -> bool:
        host = (root or "").lower()
        if not host or "." not in host:
            return True
        if host in self.CDN_DOMAINS or host in self._GENERIC_ROOTS:
            return True
        return host.split(".")[0] in self._GENERIC_LABELS

    def _public_suffix(self, host: str) -> str:
        root = self._root_domain(host)
        parts = root.split(".")
        if len(parts) < 2:
            return ""
        return ".".join(parts[1:])

    def _brand_label(self, brand: str) -> str:
        key = (brand or "").lower()
        if not key:
            return ""
        return self._BRAND_LABELS.get(key, key[:1].upper() + key[1:])

    def _strip_brand_affixes(self, label: str) -> str:
        text = (label or "").lower()
        changed = True
        while changed and len(text) >= 5:
            changed = False
            for affix in self._BRAND_AFFIXES:
                leftover = len(text) - len(affix)
                if leftover < 4:
                    continue
                if text.startswith(affix):
                    text = text[len(affix):]
                    changed = True
                    break
                if text.endswith(affix):
                    text = text[:-len(affix)]
                    changed = True
                    break
        return text

    def _brand_token(self, host: str) -> str:
        root = self._root_domain(self._clean_domain(host) or host)
        name = (root.split(".")[0] if root else "").lower()
        if not name or name in self._GENERIC_LABELS or self._is_generic_root(root):
            return ""
        brand = self._strip_brand_affixes(name)
        if not brand or brand in self._GENERIC_LABELS or len(brand) < 4:
            return ""
        return brand

    def _host_has_brand(self, host: str, brand: str) -> bool:
        brand = (brand or "").lower()
        host = (host or "").lower()
        if not host or not brand or len(brand) < 4 or brand in self._GENERIC_LABELS:
            return False
        for label in host.split("."):
            if label in self._GENERIC_LABELS:
                continue
            if label == brand or self._strip_brand_affixes(label) == brand:
                return True
            if any(label == f"{brand}{affix}" or label == f"{affix}{brand}" for affix in self._BRAND_AFFIXES):
                return True
        return False

    def _usable_block_root(self, host: str) -> str:
        cleaned = self._clean_domain(host)
        if not cleaned:
            return ""
        if cleaned.endswith(self._SKIP_HOST_SUFFIXES) or any(part.startswith("_") for part in cleaned.split(".")):
            return ""
        root = self._root_domain(cleaned)
        if not root or self._is_generic_root(root) or self._is_cdn_domain(root):
            return ""
        return root

    def _live_hosts_for_source(self, srcip: str) -> List[str]:
        """Dominios que el mismo equipo está resolviendo/usando ahora mismo (varias apps a la vez)."""
        if not srcip:
            return []
        found: List[str] = []

        def from_sessions() -> List[str]:
            hosts = []
            for row in self.get_sessions(400):
                parsed = self._normalize_session(row)
                if parsed.get("srcip") != srcip:
                    continue
                hosts.append(parsed.get("dst_host") or "")
            return hosts

        def from_fortiview() -> List[str]:
            hosts = []
            for row in self._fortiview_by_source("destination", srcip, realtime=True, count=24):
                hosts.append(self._domain_from_row(row) or str(row.get("name") or row.get("key") or ""))
            return hosts

        def from_dns() -> List[str]:
            hosts = []
            for log in self.get_dns_logs(200):
                src, _ = self._endpoint(log, "srcip", "srcaddr", "src", "source")
                if src != srcip:
                    continue
                hosts.append(str(log.get("qname") or log.get("hostname") or log.get("domain") or log.get("question") or ""))
            return hosts

        with ThreadPoolExecutor(max_workers=3) as pool:
            for fut in [pool.submit(fn) for fn in (from_sessions, from_fortiview, from_dns)]:
                try:
                    found.extend(fut.result() or [])
                except Exception as exc:
                    print(f"NOC: no se pudieron leer destinos vivos de {srcip}: {exc}")

        unique: List[str] = []
        seen: Set[str] = set()
        for value in found:
            host = self._clean_domain(value)
            if not host or host in seen:
                continue
            seen.add(host)
            unique.append(host)
        return unique

    def _expand_related_roots(self, host: str, live_hosts: Optional[List[str]] = None, platforms: Optional[List[tuple]] = None) -> tuple:
        """Junta el destino pulsado con hermanos de marca y con la plataforma que esa página abre."""
        live_hosts = live_hosts or []
        platforms = platforms or []
        bundle = self._service_bundle_for_host(host)
        roots: Set[str] = set()
        label = ""
        brand = self._brand_token(host)
        bundle_label = bundle[0] if bundle else ""

        if bundle:
            label, domains = bundle
            roots.update(domains)

        current_root = self._usable_block_root(host)
        if current_root:
            roots.add(current_root)

        if brand:
            name = (self._root_domain(host).split(".")[0] or "").lower()
            suffix = self._public_suffix(host)
            if name != brand and suffix:
                sibling = f"{brand}.{suffix}"
                if self._usable_block_root(sibling):
                    roots.add(sibling)
            label = label or self._brand_label(brand)

        # hogarymoda.com → Shopify CDN. No es "pasaba a la misma hora": la URL vive ahí.
        if not bundle:
            for _plabel, pdomains in platforms:
                roots.update(pdomains)

        target_app = (bundle_label or self._app_from_domain(host) or "").strip().lower()
        for live in live_hosts:
            live_root = self._usable_block_root(live)
            if not live_root:
                continue
            live_bundle = self._service_bundle_for_host(live)
            same_bundle = bool(bundle and live_bundle and live_bundle[0] == bundle[0])
            same_brand = bool(brand and self._host_has_brand(live, brand))
            live_app = (self._app_from_domain(live) or "").strip().lower()
            same_app = bool(
                target_app
                and live_app
                and live_app == target_app
                and not self._is_generic_app(target_app)
                and "." not in target_app
            )
            live_platform = self._platform_bundle_for_host(live)
            same_platform = bool(
                not bundle
                and live_platform
                and any(live_platform[0] == p[0] for p in platforms)
            )
            if same_bundle or same_brand or same_app or same_platform:
                roots.add(live_root)

        family = sorted(root for root in roots if root)
        return label or (f"*.{current_root}" if current_root else host), family

    def _dest_scope(self, dstip: str = "", dst_host: str = "", srcip: str = "", cascade: bool = True) -> Dict[str, Any]:
        host = self._clean_domain(dst_host)
        if host:
            if cascade:
                live_hosts: List[str] = []
                platforms: List[tuple] = []
                if srcip or not self._service_bundle_for_host(host):
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        live_f = pool.submit(self._live_hosts_for_source, srcip) if srcip else None
                        plat_f = pool.submit(self._detect_site_platforms, host) if not self._service_bundle_for_host(host) else None
                        if live_f:
                            try:
                                live_hosts = live_f.result() or []
                            except Exception as exc:
                                print(f"NOC: destinos vivos: {exc}")
                        if plat_f:
                            try:
                                platforms = plat_f.result() or []
                            except Exception as exc:
                                print(f"NOC: plataforma del sitio: {exc}")
                label, domains = self._expand_related_roots(host, live_hosts, platforms)
                if len(domains) >= 2:
                    return {
                        "kind": "fqdn_group",
                        "domains": domains,
                        "service": label,
                        "value": label,
                        "label": label,
                        "domains_label": ", ".join(f"*.{d}" for d in domains),
                    }
            root = self._usable_block_root(host) or (self._root_domain(host) if not self._is_cdn_domain(host) else "")
            if root and not self._is_generic_root(root):
                return {"kind": "fqdn", "value": f"*.{root}", "label": f"*.{root}"}
        if dstip and self._looks_like_ip(dstip):
            return {
                "kind": "ip",
                "value": dstip,
                "label": dstip,
                "warning": (
                    "Bloqueaste una IP suelta, no una página. Si ese destino usa CDN/anycast "
                    "(varias IPs rotativas), el equipo puede reconectarse por otra IP distinta. "
                    "Siempre que se detecte el dominio, se bloquea por dominio (más confiable)."
                ),
            }
        raise Exception("No hay un destino IP o página para limitar o bloquear.")

    def _ensure_address_group(self, name: str, members: List[str], comment: str = "") -> str:
        payload = {"name": name, "member": [{"name": m} for m in members], "comment": comment}
        groups = self._as_list(self._request("/firewall/addrgrp", is_cmdb=True))
        exists = any(str(row.get("name") or "") == name for row in groups)
        if exists:
            self._request(f"/firewall/addrgrp/{name}", method="PUT", payload=payload, is_cmdb=True, raise_on_error=True)
            return name
        try:
            self._request("/firewall/addrgrp", method="POST", payload=payload, is_cmdb=True, raise_on_error=True)
            return name
        except Exception as exc:
            if "-5" in str(exc) or "already" in str(exc).lower():
                self._request(f"/firewall/addrgrp/{name}", method="PUT", payload=payload, is_cmdb=True, raise_on_error=True)
                return name
            raise

    def _ensure_dest_address_object(self, dstip: str = "", dst_host: str = "", srcip: str = "", cascade: bool = True) -> Dict[str, Any]:
        scope = self._dest_scope(dstip, dst_host, srcip=srcip, cascade=cascade)
        if scope["kind"] == "ip":
            dest_name = self._create_address({
                "name": f"NOC-DST-{scope['value']}",
                "type": "ipmask",
                "subnet": f"{scope['value']} 255.255.255.255",
                "comment": "Destino NOC/SOC (IT Admin Platform)",
            })
            return {**scope, "name": dest_name}
        if scope["kind"] == "fqdn_group":
            member_names = []
            for domain in scope["domains"]:
                wc = f"*.{domain}"
                member_names.append(self._create_address({
                    "name": self._safe_object_name("NOC-FQDN", wc),
                    "type": "fqdn",
                    "fqdn": wc,
                    "comment": f"Destino FQDN NOC/SOC ({scope['service']})",
                }))
            group_name = self._safe_object_name("NOC-GRP", scope["service"])
            self._ensure_address_group(
                group_name, member_names, comment=f"Bloqueo/limite {scope['service']} (IT Admin Platform)"
            )
            return {**scope, "name": group_name}
        dest_name = self._create_address({
            "name": self._safe_object_name("NOC-FQDN", scope["value"]),
            "type": "fqdn",
            "fqdn": scope["value"],
            "comment": "Destino FQDN NOC/SOC (IT Admin Platform)",
        })
        return {**scope, "name": dest_name}

    def _dests_covered_by(self, dest: Dict[str, Any]) -> Set[str]:
        """FQDN sueltos (spotify.com + spotifycdn.com) que ya quedan dentro del grupo nuevo."""
        if dest.get("kind") != "fqdn_group":
            return set()
        wanted = set()
        for domain in dest.get("domains") or []:
            wanted.add(str(domain).lower())
            wanted.add(f"*.{domain}".lower())
        addresses = self._as_list(self._request("/firewall/address", is_cmdb=True))
        groups = self._as_list(self._request("/firewall/addrgrp", is_cmdb=True))
        addr_by_name = {row.get("name"): row for row in addresses}
        covered: Set[str] = set()
        for row in addresses:
            fqdn = str(row.get("fqdn") or "").lower()
            if fqdn in wanted and row.get("name"):
                covered.add(str(row.get("name")))
        for row in groups:
            name = str(row.get("name") or "")
            if not name or name == dest.get("name"):
                continue
            members = [m.get("name") for m in (row.get("member") or []) if isinstance(m, dict)]
            member_fqdns = {str((addr_by_name.get(m) or {}).get("fqdn") or "").lower() for m in members}
            member_fqdns.discard("")
            if member_fqdns and member_fqdns <= wanted:
                covered.add(name)
        return covered

    def apply_destination_shaper(
        self,
        srcip: str,
        shaper_name: str = "",
        dstip: str = "",
        dst_host: str = "",
        srcintf: str = "",
        dstintf: str = "",
        max_mbps: Any = None,
    ) -> Any:
        """Limita el ancho de banda de un equipo SOLO hacia esa página/destino. El resto del PC sigue normal."""
        shaper_name = self._ensure_named_shaper(shaper_name, max_mbps)
        src_name = self._ensure_host_address_object(srcip)
        dest = self._ensure_dest_address_object(dstip, dst_host, srcip=srcip, cascade=True)
        policy_name = self._safe_object_name("NOC-DSHAPE", srcip, dest["value"])
        dest_names = [dest["name"]]
        if dstip and self._looks_like_ip(dstip):
            dest_names.append(self._create_address({
                "name": f"NOC-DST-{dstip}",
                "type": "ipmask",
                "subnet": f"{dstip} 255.255.255.255",
                "comment": "IP viva del destino al limitar (FQDN wildcard no siempre pega Cloudflare).",
            }))
        existing_policies = self._as_list(self._request("/firewall/shaping-policy", is_cmdb=True))
        existing = next((p for p in existing_policies if p.get("name") == policy_name), None)
        detail = dest.get("domains_label") or dest["label"]
        payload = self._shaping_payload(
            policy_name,
            f"Límite {shaper_name} {srcip} → {detail}",
            [src_name],
            dest_names,
            shaper_name,
            srcintf=srcintf,
            dstintf=dstintf,
        )
        policy_key = self._shaping_policy_id(existing)
        if existing and policy_key is not None:
            data = self._request(
                f"/firewall/shaping-policy/{policy_key}",
                method="PUT",
                payload=payload,
                is_cmdb=True,
                raise_on_error=True,
            )
        else:
            data = self._request("/firewall/shaping-policy", method="POST", payload=payload, is_cmdb=True, raise_on_error=True)
        return {
            "policy": policy_name,
            "dest": dest["label"],
            "domains_label": dest.get("domains_label"),
            "warning": dest.get("warning"),
            "mbps": self._mbps_of_shaper(shaper_name)[0],
            "data": data,
        }

    def _policy_member_names(self, policy: Dict[str, Any], field: str) -> List[str]:
        names = []
        for row in policy.get(field) or []:
            if isinstance(row, dict) and row.get("name"):
                names.append(str(row["name"]))
            elif isinstance(row, str) and row:
                names.append(row)
        return names

    def _is_quota_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return "-4" in text or "maximum number of entries" in text or "reached the maximum" in text

    def _move_policy_before_first_accept(self, policy_id: Any, policies: List[Dict[str, Any]]) -> None:
        first_accept = next(
            (self._shaping_policy_id(p) for p in policies if str(p.get("action")) == "accept" and str(p.get("status") or "enable") != "disable"),
            None,
        )
        if policy_id and first_accept and str(policy_id) != str(first_accept):
            self._request(
                f"/firewall/policy/{policy_id}",
                method="PUT",
                params={"action": "move", "before": str(first_accept)},
                is_cmdb=True,
                raise_on_error=True,
            )

    def _delete_policy(self, policy_id: Any) -> None:
        if policy_id is None:
            return
        self._request(f"/firewall/policy/{policy_id}", method="DELETE", is_cmdb=True, raise_on_error=True)

    def _noc_block_policies(self, policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for policy in policies:
            name = str(policy.get("name") or "")
            comments = str(policy.get("comments") or policy.get("comment") or "")
            if name.startswith("NOC-DBLOCK") or comments.startswith("Bloqueo destino NOC"):
                rows.append(policy)
        return rows

    def _policies_for_src(self, policies: List[Dict[str, Any]], src_name: str, srcip: str) -> List[Dict[str, Any]]:
        matches = []
        for policy in self._noc_block_policies(policies):
            members = self._policy_member_names(policy, "srcaddr")
            if src_name in members or any(srcip in member for member in members):
                matches.append(policy)
        return matches

    def _deny_payload(self, policy_name: str, src_names: List[str], dest_names: List[str], comment: str) -> Dict[str, Any]:
        unique_src = list(dict.fromkeys([n for n in src_names if n]))
        unique_dst = list(dict.fromkeys([n for n in dest_names if n]))
        return {
            "name": policy_name[:35],
            "srcintf": [{"name": "any"}],
            "dstintf": [{"name": "any"}],
            "srcaddr": [{"name": name} for name in unique_src],
            "dstaddr": [{"name": name} for name in unique_dst],
            "service": [{"name": "ALL"}],
            "schedule": "always",
            "action": "deny",
            "status": "enable",
            "logtraffic": "all",
            "comments": comment[:255],
        }

    def _consolidate_noc_block_policies(self, policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Junta bloqueos NOC duplicados del mismo origen. En VMs con 3 políticas esto libera cupos."""
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for policy in self._noc_block_policies(policies):
            key = ",".join(sorted(self._policy_member_names(policy, "srcaddr"))) or str(policy.get("policyid"))
            groups.setdefault(key, []).append(policy)

        deleted = False
        for rows in groups.values():
            if len(rows) < 2:
                continue
            primary = rows[0]
            dests: List[str] = []
            srcs: List[str] = []
            for row in rows:
                dests.extend(self._policy_member_names(row, "dstaddr"))
                srcs.extend(self._policy_member_names(row, "srcaddr"))
            payload = self._deny_payload(
                str(primary.get("name") or "NOC-DBLOCK"),
                srcs,
                dests,
                str(primary.get("comments") or "Bloqueo destino NOC (consolidado)."),
            )
            self._request(
                f"/firewall/policy/{primary.get('policyid')}",
                method="PUT",
                payload=payload,
                is_cmdb=True,
                raise_on_error=True,
            )
            for extra in rows[1:]:
                try:
                    self._delete_policy(extra.get("policyid"))
                    deleted = True
                except Exception as exc:
                    print(f"No se pudo borrar política NOC {extra.get('policyid')}: {exc}")

        if deleted:
            return self._as_list(self._request("/firewall/policy", is_cmdb=True))
        return policies

    def preview_destination_block(self, srcip: str, dstip: str = "", dst_host: str = "") -> Dict[str, Any]:
        """Dice si hay familia para preguntar cascada, sin tocar el FortiGate."""
        selected = self._dest_scope(dstip, dst_host, srcip="", cascade=False)
        family = self._dest_scope(dstip, dst_host, srcip=srcip, cascade=True)
        can_cascade = family.get("kind") == "fqdn_group" and len(family.get("domains") or []) >= 2
        selected_label = selected.get("label") or dst_host or dstip
        return {
            "selected": selected_label,
            "service": family.get("service") if can_cascade else "",
            "can_cascade": can_cascade,
            "domains": family.get("domains") or [],
            "domains_label": family.get("domains_label") if can_cascade else selected_label,
        }

    def block_destination(self, srcip: str, dstip: str = "", dst_host: str = "", cascade: bool = True) -> Any:
        """Niega origen → página. Reutiliza UNA política por equipo: las VM suelen tener tope de 3."""
        src_name = self._ensure_host_address_object(srcip)
        dest = self._ensure_dest_address_object(dstip, dst_host, srcip=srcip, cascade=cascade)
        policy_name = self._safe_object_name("NOC-DBLOCK", srcip)
        policies = self._consolidate_noc_block_policies(self._as_list(self._request("/firewall/policy", is_cmdb=True)))
        mine = self._policies_for_src(policies, src_name, srcip)
        detail = dest.get("domains_label") or dest["label"]
        warning = dest.get("warning")
        subsumed = self._dests_covered_by(dest)
        dest_names = [dest["name"]]
        for row in mine:
            for name in self._policy_member_names(row, "dstaddr"):
                if name == dest["name"] or name in subsumed or name in dest_names:
                    continue
                dest_names.append(name)

        payload = self._deny_payload(
            policy_name,
            [src_name],
            dest_names,
            f"Bloqueo destino NOC: {srcip} → {detail}. El host no se aísla.",
        )

        result = None
        policy_id = None
        reused = False
        if mine:
            primary = mine[0]
            result = self._request(
                f"/firewall/policy/{primary.get('policyid')}",
                method="PUT",
                payload=payload,
                is_cmdb=True,
                raise_on_error=True,
            )
            policy_id = primary.get("policyid")
            reused = True
            for extra in mine[1:]:
                try:
                    self._delete_policy(extra.get("policyid"))
                except Exception as exc:
                    print(f"No se pudo borrar política NOC extra {extra.get('policyid')}: {exc}")
        else:
            try:
                result = self._request("/firewall/policy", method="POST", payload=payload, is_cmdb=True, raise_on_error=True)
                if isinstance(result, dict):
                    policy_id = result.get("mkey") or result.get("policyid")
            except Exception as exc:
                if not self._is_quota_error(exc):
                    raise
                # Tope de la VM: no hay cupo para otra política. Reusar una NOC existente.
                policies = self._consolidate_noc_block_policies(self._as_list(self._request("/firewall/policy", is_cmdb=True)))
                mine = self._policies_for_src(policies, src_name, srcip)
                shared = mine[0] if mine else (self._noc_block_policies(policies)[0] if self._noc_block_policies(policies) else None)
                if shared:
                    src_names = self._policy_member_names(shared, "srcaddr") + [src_name]
                    dest_names = self._policy_member_names(shared, "dstaddr") + [dest["name"]]
                    shared_name = str(shared.get("name") or policy_name)
                    payload = self._deny_payload(
                        shared_name,
                        src_names,
                        dest_names,
                        f"Bloqueo destino NOC compartido (tope de políticas): {srcip} → {detail}.",
                    )
                    result = self._request(
                        f"/firewall/policy/{shared.get('policyid')}",
                        method="PUT",
                        payload=payload,
                        is_cmdb=True,
                        raise_on_error=True,
                    )
                    policy_id = shared.get("policyid")
                    policy_name = shared_name
                    reused = True
                    if src_name not in self._policy_member_names(shared, "srcaddr"):
                        warning = (
                            (warning + " ") if warning else ""
                        ) + (
                            "Este FortiGate VM ya no admite más políticas. El bloqueo se agregó a una "
                            "política NOC existente: los equipos que ya estaban en esa regla también "
                            "quedan sin esos destinos."
                        )
                else:
                    raise Exception(
                        "Este FortiGate llegó al tope de políticas de firewall (error -4) y no hay "
                        "una regla NOC que se pueda reutilizar. Borra una política vieja en el "
                        "FortiGate o sube la licencia de la VM."
                    ) from exc

        self._move_policy_before_first_accept(policy_id, policies)
        return {
            "policy": policy_name,
            "dest": dest["label"],
            "dest_name": dest["name"],
            "domains_label": dest.get("domains_label"),
            "warning": warning,
            "cascade": dest.get("kind") == "fqdn_group",
            "policyid": policy_id,
            "reused": reused,
            "data": result,
        }

    def _host_ip_from_object(self, name: str, addresses: Dict[str, Any]) -> str:
        if str(name).startswith("NOC-HOST-"):
            return str(name).replace("NOC-HOST-", "", 1)
        addr = addresses.get(name) or {}
        subnet = str(addr.get("subnet") or "").strip()
        return subnet.split()[0] if subnet else str(name)

    def _dest_meta(self, dest_name: str, addresses: Dict[str, Any], groups: Dict[str, Any]) -> Dict[str, str]:
        if dest_name.startswith("NOC-GRP-"):
            label = dest_name.replace("NOC-GRP-", "", 1)
            group = groups.get(dest_name) or {}
            member_names = [m.get("name") for m in (group.get("member") or []) if isinstance(m, dict) and m.get("name")]
            domains = []
            for member in member_names:
                fqdn = str((addresses.get(member) or {}).get("fqdn") or "").strip()
                if fqdn:
                    domains.append(fqdn)
            return {
                "dest_label": label,
                "domains_label": ", ".join(domains) or label,
            }
        addr = addresses.get(dest_name) or {}
        fqdn = str(addr.get("fqdn") or "").strip()
        if fqdn:
            return {"dest_label": fqdn, "domains_label": fqdn}
        subnet = str(addr.get("subnet") or "").strip()
        if subnet:
            ip = subnet.split()[0]
            return {"dest_label": ip, "domains_label": ip}
        return {"dest_label": dest_name, "domains_label": dest_name}

    def list_destination_blocks(self) -> List[Dict[str, Any]]:
        """Lee del FortiGate las políticas NOC-DBLOCK que un operador aplicó a mano."""
        policies = self._as_list(self._request("/firewall/policy", is_cmdb=True))
        addresses = {row.get("name"): row for row in self._as_list(self._request("/firewall/address", is_cmdb=True))}
        groups = {row.get("name"): row for row in self._as_list(self._request("/firewall/addrgrp", is_cmdb=True))}
        rows = []
        for policy in self._noc_block_policies(policies):
            srcs = [
                self._host_ip_from_object(name, addresses)
                for name in self._policy_member_names(policy, "srcaddr")
            ]
            for dest_name in self._policy_member_names(policy, "dstaddr"):
                meta = self._dest_meta(dest_name, addresses, groups)
                for srcip in srcs:
                    rows.append({
                        "srcip": srcip,
                        "dest_name": dest_name,
                        "dest_label": meta["dest_label"],
                        "domains_label": meta["domains_label"],
                        "policy": policy.get("name"),
                        "policyid": policy.get("policyid"),
                        "comment": policy.get("comments") or policy.get("comment") or "",
                        "status": policy.get("status") or "enable",
                        "kind": "destination_block",
                    })
        return rows

    def unblock_destination(self, srcip: str, dest_name: str = "") -> Any:
        """Quita un destino (o todos) del bloqueo NOC de ese equipo. Solo se ejecuta si un humano lo pide."""
        src_name = f"NOC-HOST-{srcip}"
        policies = self._as_list(self._request("/firewall/policy", is_cmdb=True))
        mine = self._policies_for_src(policies, src_name, srcip)
        if not mine:
            raise Exception(f"No hay un bloqueo de página activo para {srcip} en este FortiGate.")

        removed: List[str] = []
        for policy in mine:
            dests = self._policy_member_names(policy, "dstaddr")
            srcs = self._policy_member_names(policy, "srcaddr")
            if dest_name:
                keep = [name for name in dests if name != dest_name]
            else:
                keep = []
            dropped = [name for name in dests if name not in keep]
            if not dropped:
                continue
            removed.extend(dropped)
            only_this_host = srcs == [src_name] or (len(srcs) == 1 and srcip in "".join(srcs))
            if keep:
                payload = self._deny_payload(
                    str(policy.get("name") or self._safe_object_name("NOC-DBLOCK", srcip)),
                    srcs if not only_this_host else [src_name],
                    keep,
                    f"Bloqueo destino NOC: {srcip} (actualizado).",
                )
                self._request(
                    f"/firewall/policy/{policy.get('policyid')}",
                    method="PUT",
                    payload=payload,
                    is_cmdb=True,
                    raise_on_error=True,
                )
            elif only_this_host:
                self._delete_policy(policy.get("policyid"))
            else:
                leftover_src = [name for name in srcs if name != src_name and srcip not in name]
                if leftover_src:
                    payload = self._deny_payload(
                        str(policy.get("name") or "NOC-DBLOCK"),
                        leftover_src,
                        dests,
                        str(policy.get("comments") or "Bloqueo destino NOC."),
                    )
                    self._request(
                        f"/firewall/policy/{policy.get('policyid')}",
                        method="PUT",
                        payload=payload,
                        is_cmdb=True,
                        raise_on_error=True,
                    )
                else:
                    self._delete_policy(policy.get("policyid"))

        if not removed:
            raise Exception(
                f"No se encontró el destino '{dest_name or 'indicado'}' en los bloqueos de {srcip}."
            )
        return {"srcip": srcip, "removed": removed, "dest_name": dest_name}

    def apply_traffic_shaper(
        self,
        target_ip: str,
        shaper_name: str = "",
        max_mbps: Any = None,
        direction: str = "symmetric",
        origin: str = "manual",
    ) -> Any:
        """Limita el ancho de banda de TODO el tráfico de esa IP, no solo una página."""
        shaper_name = self._ensure_named_shaper(shaper_name, max_mbps)
        address_name = self._ensure_host_address_object(target_ip)
        policy_name = f"NOC-SHAPE-{target_ip}"
        direction = "rx" if str(direction or "").lower() == "rx" else "symmetric"
        origin = "preset" if str(origin or "").lower() == "preset" else "manual"
        existing_policies = self._as_list(self._request("/firewall/shaping-policy", is_cmdb=True))
        existing = next((p for p in existing_policies if p.get("name") == policy_name), None)
        payload = self._shaping_payload(
            policy_name,
            f"Traffic shaping NOC ({shaper_name}) dir={direction} origen={origin}",
            [address_name],
            ["all"],
            shaper_name,
            direction=direction,
        )
        policy_key = self._shaping_policy_id(existing)
        if existing and policy_key is not None:
            return self._request(
                f"/firewall/shaping-policy/{policy_key}", method="PUT", payload=payload, is_cmdb=True, raise_on_error=True
            )
        return self._request("/firewall/shaping-policy", method="POST", payload=payload, is_cmdb=True, raise_on_error=True)

    def list_shaping_assignments(self) -> List[Dict[str, Any]]:
        """Límites NOC: por equipo entero (NOC-SHAPE) o por página (NOC-DSHAPE)."""
        policies = self._as_list(self._request("/firewall/shaping-policy", is_cmdb=True))
        assignments = []
        for policy in policies:
            name = str(policy.get("name") or "")
            if not (name.startswith("NOC-SHAPE-") or name.startswith("NOC-DSHAPE-")):
                continue
            raw_shaper = str(policy.get("per-ip-shaper") or policy.get("traffic-shaper-reverse") or "")
            shaper = raw_shaper.replace("-pipe", "")
            mbps, label = self._mbps_of_shaper(shaper)
            srcs = self._policy_member_names(policy, "srcaddr")
            dests = self._policy_member_names(policy, "dstaddr")
            srcip = ""
            for src in srcs:
                if str(src).startswith("NOC-HOST-"):
                    srcip = str(src).replace("NOC-HOST-", "", 1)
                    break
            if not srcip and name.startswith("NOC-SHAPE-"):
                srcip = name.replace("NOC-SHAPE-", "", 1)
            scope = "host" if name.startswith("NOC-SHAPE-") else "destination"
            if scope == "host" or dests == ["all"]:
                dest_label = "Todo el equipo"
                scope = "host"
            else:
                dest_label = dests[0] if dests else name
                if dest_label.startswith("NOC-GRP-"):
                    dest_label = dest_label.replace("NOC-GRP-", "", 1)
                elif dest_label.startswith("NOC-FQDN-"):
                    dest_label = dest_label.replace("NOC-FQDN-", "", 1)
            comment = str(policy.get("comment") or policy.get("comments") or "")
            has_fwd = bool(str(policy.get("traffic-shaper") or "").strip())
            has_rev = bool(str(policy.get("traffic-shaper-reverse") or "").strip())
            if "dir=rx" in comment or (has_rev and not has_fwd):
                direction = "rx"
            else:
                direction = "symmetric"
            if "origen=preset" in comment:
                origin = "preset"
            elif "origen=manual" in comment:
                origin = "manual"
            elif scope == "destination":
                origin = "destination"
            else:
                origin = "preset" if mbps in (2, 5, 10, 20, 50) else "manual"
            assignments.append({
                "ip": srcip or name,
                "srcip": srcip,
                "dest_label": dest_label,
                "policy_name": name,
                "policyid": self._shaping_policy_id(policy),
                "shaper": shaper,
                "label": label,
                "mbps": mbps,
                "status": policy.get("status") or "enable",
                "scope": scope,
                "direction": direction,
                "origin": origin,
            })
        return assignments

    def remove_traffic_shaper(self, target_ip: str = "", policy_name: str = "") -> Any:
        """Quita un límite NOC (equipo entero o una página). Solo si un humano lo pide."""
        policies = self._as_list(self._request("/firewall/shaping-policy", is_cmdb=True))
        existing = None
        if policy_name:
            if not (policy_name.startswith("NOC-SHAPE-") or policy_name.startswith("NOC-DSHAPE-")):
                raise Exception("Solo se pueden quitar límites creados por esta plataforma.")
            existing = next((p for p in policies if p.get("name") == policy_name), None)
        elif target_ip:
            host_name = f"NOC-SHAPE-{target_ip}"
            existing = next((p for p in policies if p.get("name") == host_name), None)
            if not existing:
                existing = next((p for p in policies if p.get("name") == target_ip), None)
        if not existing:
            raise Exception("No hay un límite de ancho de banda con ese nombre en este FortiGate.")
        key = self._shaping_policy_id(existing)
        if key is None:
            raise Exception("No se pudo identificar la política de límite para borrarla.")
        return self._request(
            f"/firewall/shaping-policy/{key}", method="DELETE", is_cmdb=True, raise_on_error=True
        )

    def find_application_id(self, app_name: str) -> Optional[int]:
        """Busca en la base de firmas de FortiGuard (application/rule) el ID de una app por nombre."""
        rows = self._as_list(self._request("/application/rule", params={"filter": f"name=={app_name}"}, is_cmdb=True))
        if not rows:
            rows = self._as_list(self._request("/application/rule", params={"filter": f"name=@{app_name}"}, is_cmdb=True))
        exact = next((r for r in rows if str(r.get("name", "")).lower() == app_name.lower()), None)
        if exact:
            return exact.get("id")
        return rows[0].get("id") if rows else None

    def block_application(self, app_name: str, profile_name: str = "default") -> Any:
        """Añade la firma de una aplicación a la lista negra de un perfil de Application Control."""
        app_id = self.find_application_id(app_name)
        if not app_id:
            raise Exception(f"No se encontró la firma de '{app_name}' en la base FortiGuard de este equipo.")

        profile = self._request(f"/application/list/{profile_name}", is_cmdb=True)
        if not profile or isinstance(profile, list):
            raise Exception(f"El perfil de control de aplicaciones '{profile_name}' no existe en este FortiGate.")

        entries = profile.get("entries", []) or []
        already_blocked = any(
            e.get("action") == "block" and any(a.get("id") == app_id for a in (e.get("application") or []))
            for e in entries
        )
        if already_blocked:
            return {"status": "already_blocked", "application_id": app_id}

        next_id = max([e.get("id", 0) for e in entries], default=0) + 1
        entries.append({
            "id": next_id,
            "application": [{"id": app_id}],
            "action": "block",
            "log": "enable",
        })
        return self._request(
            f"/application/list/{profile_name}", method="PUT", payload={"entries": entries}, is_cmdb=True, raise_on_error=True
        )

    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Combines various endpoints to return a comprehensive diagnostic overview.
        """
        # 1. Obtener alias de interfaces
        interfaces_data = self._request("/system/interface", is_cmdb=True)
        if not isinstance(interfaces_data, list):
            interfaces_data = []
        
        alias_map = {}
        for iface in interfaces_data:
            name = iface.get("name")
            alias = iface.get("alias", "").strip()
            if name:
                alias_map[name] = f"{alias} ({name})" if alias else name

        # 2. DHCP Leases
        dhcp_leases = self._request("/system/dhcp")
        if not isinstance(dhcp_leases, list):
            dhcp_leases = []
            
        for lease in dhcp_leases:
            iface_name = lease.get("interface")
            if iface_name and iface_name in alias_map:
                lease["interface_alias"] = alias_map[iface_name]
            
        # 3. Routing (Segmentation)
        routing = self._request("/router/ipv4")
        if not isinstance(routing, list):
            routing = []
            
        # Filter connected routes to determine local LAN segments
        segments = []
        for r in routing:
            if r.get("type") == "connect" and r.get("gateway") == "0.0.0.0":
                iface_name = r.get("interface")
                if iface_name and iface_name in alias_map:
                    r["interface_alias"] = alias_map[iface_name]
                segments.append(r)

        return {
            "dhcp_leases": dhcp_leases,
            "segments": segments,
            "top_consumers": []
        }

    def _interface_alias_map(self) -> Dict[str, str]:
        alias_map: Dict[str, str] = {}
        for iface in self._as_list(self._request("/system/interface", is_cmdb=True)):
            name = str(iface.get("name") or "")
            if not name:
                continue
            alias = str(iface.get("alias") or "").strip()
            alias_map[name] = f"{alias} ({name})" if alias else name
        return alias_map

    def _identity_from_vci(self, vci: str) -> tuple:
        blob = str(vci or "").lower()
        if not blob:
            return "", ""
        if "msft" in blob or "microsoft" in blob:
            return "Windows", "Microsoft"
        if "android" in blob:
            return "Android", "Google"
        if "apple" in blob:
            return "macOS/iOS", "Apple"
        if "hikvision" in blob:
            return "IPCamera", "Hikvision"
        if "vmware" in blob:
            return "Virtual Machine", "VMware"
        if "udhcp" in blob or "busybox" in blob:
            return "Linux", ""
        return "", str(vci).strip()[:40]

    def list_hosts(self) -> List[Dict[str, Any]]:
        """Inventario real: device identification + DHCP + ARP. Nada inventado."""
        alias_map = self._interface_alias_map()
        merged: Dict[str, Dict[str, Any]] = {}

        def iface_label(name: str) -> str:
            raw = str(name or "").strip()
            return alias_map.get(raw) or raw

        def upsert(ip: str = "", mac: str = "", hostname: str = "", os_name: str = "", vendor: str = "", iface: str = "") -> None:
            ip_n = str(ip or "").strip().split("/")[0]
            mac_n = self._normalize_mac(mac)
            key = mac_n or ip_n
            if not key:
                return
            row = merged.get(key) or {
                "ip": "",
                "mac": "",
                "hostname": "",
                "os": "",
                "vendor": "",
                "iface": "",
            }
            if ip_n:
                row["ip"] = ip_n
            if mac_n:
                row["mac"] = mac_n
            if hostname and (not row["hostname"] or row["hostname"] in ("*", "unknown")):
                row["hostname"] = hostname
            if os_name and not row["os"]:
                row["os"] = os_name
            if vendor and not row["vendor"]:
                row["vendor"] = vendor
            if iface and not row["iface"]:
                row["iface"] = iface_label(iface)
            merged[key] = row

        for endpoint in ("/user/device/query", "/user/device", "/user/detected-device"):
            params = {"count": 1000} if "query" in endpoint else None
            for row in self._as_list(self._request(endpoint, params=params, timeout=12)):
                mac = row.get("mac") or row.get("mac_address") or row.get("hw_addr") or ""
                ip = row.get("ipv4_address") or row.get("ip") or row.get("addr") or row.get("ipv4") or ""
                if isinstance(ip, list) and ip:
                    ip = ip[0]
                hostname = row.get("hostname") or row.get("host") or row.get("name") or ""
                os_name = row.get("os") or row.get("os_name") or row.get("osname") or row.get("device_os") or ""
                vendor = (
                    row.get("hardware_vendor")
                    or row.get("hardware")
                    or row.get("vendor")
                    or row.get("type")
                    or row.get("device_type")
                    or ""
                )
                iface = row.get("interface") or row.get("srcintf") or row.get("master_intf") or ""
                upsert(str(ip), str(mac), str(hostname), str(os_name), str(vendor), str(iface))

        for lease in self._as_list(self._request("/system/dhcp", timeout=8)):
            vci = str(lease.get("vci") or lease.get("vendor") or lease.get("vendor_class") or "")
            os_name, vendor = self._identity_from_vci(vci)
            upsert(
                str(lease.get("ip") or ""),
                str(lease.get("mac") or ""),
                str(lease.get("hostname") or lease.get("host") or ""),
                os_name,
                vendor,
                str(lease.get("interface") or ""),
            )

        for arp in self._as_list(self._request("/network/arp", timeout=8)):
            upsert(
                str(arp.get("ip") or arp.get("address") or ""),
                str(arp.get("mac") or arp.get("hw_addr") or ""),
                str(arp.get("hostname") or ""),
                "",
                "",
                str(arp.get("interface") or arp.get("intf") or ""),
            )

        hosts = list(merged.values())
        hosts.sort(key=lambda row: str(row.get("hostname") or row.get("ip") or "").lower())
        return hosts

    def _as_list(self, raw: Any) -> List[Dict[str, Any]]:
        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]
        if isinstance(raw, dict):
            for key in ("details", "data", "sessions", "statistics", "rows", "values", "items"):
                val = raw.get(key)
                if isinstance(val, list):
                    return [x for x in val if isinstance(x, dict)]
                if isinstance(val, dict):
                    nested = self._as_list(val)
                    if nested:
                        return nested
            if any(raw.get(k) not in (None, "") for k in ("srcip", "srcaddr", "src", "saddr", "dstip", "dst", "addr", "name", "ip")):
                return [raw]
        return []

    def _fortiview(self, report_by: str, realtime: bool = True, start: Optional[int] = None, end: Optional[int] = None, count: int = 15, extra: Optional[Dict] = None) -> List[Dict[str, Any]]:
        params = {
            "report_by": report_by,
            "sort_by": "bytes",
            "count": count,
            "ip_version": "ipv4",
        }
        if realtime:
            params["realtime"] = "true"
        else:
            params["realtime"] = "false"
            params["device"] = "disk"
            if start:
                params["start"] = int(start)
            if end:
                params["end"] = int(end)
        if extra:
            params.update(extra)

        # FortiOS 8: /fortiview/statistics y /firewall/session dan 404.
        # Lo que responde en Playa es realtime-statistics / historical-statistics.
        if realtime:
            endpoints = ["/fortiview/realtime-statistics", "/fortiview/statistics"]
        else:
            endpoints = ["/fortiview/historical-statistics", "/fortiview/statistics"]

        for endpoint in endpoints:
            rows = self._as_list(self._request(endpoint, params=params, timeout=10))
            if rows:
                return rows
        return []

    def _fortiview_by_source(self, report_by: str, srcip: str, realtime: bool = True, count: int = 8) -> List[Dict[str, Any]]:
        if not srcip:
            return []
        rows = self._fortiview(report_by, realtime=realtime, count=count, extra={"filter": f"srcip=={srcip}"})
        if rows:
            return rows
        return self._fortiview(report_by, realtime=realtime, count=count, extra={"srcip": srcip})

    def get_dns_logs(self, rows: int = 200) -> List[Dict[str, Any]]:
        for endpoint in ("/disk/dns", "/memory/dns"):
            logs = self._as_list(self._request(endpoint, params={"rows": rows}, is_log=True, timeout=12))
            if logs:
                return logs
        return []

    def get_sessions(self, count: int = 400) -> List[Dict[str, Any]]:
        params = {"count": min(max(count, 1), 500), "ip_version": "ipv4", "summary": "false"}
        # FortiOS 8 usa /firewall/sessions (plural). FortiOS 7 sigue en /firewall/session.
        for endpoint in ("/firewall/sessions", "/firewall/session"):
            rows = self._as_list(self._request(endpoint, params=params, timeout=12))
            if rows:
                return rows
        return []

    def get_traffic_logs(self, start: Optional[int] = None, end: Optional[int] = None, rows: int = 200) -> List[Dict[str, Any]]:
        params = {"rows": rows}
        logs = self._as_list(self._request("/disk/traffic/forward", params=params, is_log=True, timeout=10))
        if not logs:
            logs = self._as_list(self._request("/memory/traffic/forward", params=params, is_log=True, timeout=8))
        if start or end:
            filtered = []
            for log in logs:
                ts = self._log_timestamp(log)
                if start and ts and ts < int(start):
                    continue
                if end and ts and ts > int(end):
                    continue
                filtered.append(log)
            return filtered
        return logs

    def _log_timestamp(self, log: Dict[str, Any]) -> Optional[int]:
        for key in ("_metadata.timestamp", "eventtime", "timestamp"):
            val = log.get(key)
            if val:
                try:
                    n = int(val)
                    return n // 1000000000 if n > 10**12 else n
                except (TypeError, ValueError):
                    continue
        date = log.get("date")
        time_str = log.get("time")
        if date and time_str:
            try:
                dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
                return int(dt.replace(tzinfo=timezone.utc).timestamp())
            except ValueError:
                return None
        return None

    def _as_int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _row_tx_rx(self, row: Dict[str, Any]) -> tuple:
        sent = row.get("tx_bytes") or row.get("sentbyte") or row.get("sent") or row.get("bytes_sent") or 0
        recv = row.get("rx_bytes") or row.get("rcvdbyte") or row.get("rcvd") or row.get("bytes_received") or 0
        tx = self._as_int(sent)
        rx = self._as_int(recv)
        if tx or rx:
            return tx, rx
        total = 0
        for key in ("bytes", "tot_bytes", "total_bytes"):
            if row.get(key) not in (None, ""):
                total = self._as_int(row[key])
                break
        return 0, total

    def _row_bytes(self, row: Dict[str, Any]) -> int:
        tx, rx = self._row_tx_rx(row)
        if tx or rx:
            return tx + rx
        for key in ("bytes", "tot_bytes", "total_bytes"):
            if row.get(key) not in (None, ""):
                return self._as_int(row[key])
        return 0

    def _looks_like_ip(self, value: Any) -> bool:
        text = str(value or "")
        if ":" in text and text.count(".") == 3:
            text = text.rsplit(":", 1)[0]
        parts = text.split(".")
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False

    def _is_private_ip(self, value: str) -> bool:
        ip = str(value or "").split(":")[0]
        return (
            ip.startswith("10.")
            or ip.startswith("192.168.")
            or ip.startswith("127.")
            or any(ip.startswith(f"172.{n}.") for n in range(16, 32))
        )

    def _split_endpoint(self, value: Any) -> tuple:
        if value in (None, ""):
            return "", ""
        if isinstance(value, dict):
            return str(value.get("ip") or value.get("addr") or ""), str(value.get("port") or "")
        text = str(value).strip()
        if text.count(".") == 3 and ":" in text:
            ip, port = text.rsplit(":", 1)
            if port.isdigit():
                return ip, port
        return text, ""

    def _endpoint(self, row: Dict[str, Any], *keys: str) -> tuple:
        for key in keys:
            if key in row and row.get(key) not in (None, ""):
                ip, port = self._split_endpoint(row.get(key))
                if ip:
                    return ip, port
        return "", ""

    PROTOCOL_LABELS = {
        "", "—", "-", "unknown", "none", "n/a", "null",
        "http", "https", "ssl", "tcp", "udp", "ip", "icmp",
        "dns", "ntp", "snmp", "dhcp", "ssh", "ftp", "telnet",
        "smtp", "smtps", "pop3", "pop3s", "imap", "imaps",
        "smb", "rdp", "ldap", "ldaps", "dot", "mdns", "upnp",
        "rpc", "netbios", "sip", "xmpp",
        "tráfico no clasificado", "trafico no clasificado",
        "tráfico agregado", "trafico agregado",
        "uncategorized", "unclassified", "other", "misc",
    }
    NOISE_PORTS = {53, 67, 68, 123, 161, 162, 5353, 853}
    NOISE_APPS = {"dns", "ntp", "snmp", "dhcp", "icmp", "mdns", "dot"}

    def _is_generic_app(self, name: Any) -> bool:
        return str(name or "").strip().lower() in {
            "", "—", "-", "unknown", "none", "n/a", "null",
            "tráfico no clasificado", "trafico no clasificado",
            "tráfico agregado", "trafico agregado",
            "uncategorized", "unclassified", "other", "misc",
        }

    def _is_protocol_label(self, name: Any) -> bool:
        return str(name or "").strip().lower() in self.PROTOCOL_LABELS

    def _named_app(self, row: Dict[str, Any]) -> str:
        for key in (
            "app", "application", "appname", "app_name",
            "cloudapp", "cloud_app", "dstname", "webdomain", "domain",
            "hostname", "appcat", "category", "service",
        ):
            val = str(row.get(key) or "").strip()
            if self._is_generic_app(val) or self._looks_like_ip(val) or self._is_protocol_label(val):
                continue
            if self._is_cdn_label(val):
                continue
            return val.upper() if val.isalpha() else val
        return ""

    CDN_LABELS = {"cloudflare", "akamai", "akamai cdn", "fastly", "cloudfront", "incapsula", "cdn77", "stackpath"}
    CDN_DOMAINS = (
        "cloudflare.com", "cloudflare.net", "cloudflare-dns.com",
        "akamai.net", "akamaiedge.net", "akamaihd.net", "edgekey.net",
        "fastly.net", "cloudfront.net", "amazonaws.com",
    )
    DOMAIN_APPS = (
        (("youtube.", "youtu.be", "googlevideo.", "ytimg.", "ggpht."), "YouTube"),
        (("twitch.", "ttvnw.", "jtvnw.", "justin.tv"), "Twitch"),
        (("discord.", "discordapp.", "discord.gg"), "Discord"),
        (("steam", "steampowered.", "steamcontent.", "steamstatic."), "Steam"),
        (("netflix.", "nflxvideo.", "nflximg."), "Netflix"),
        (("spotify.", "spotifycdn.", "pscdn.co", "scdn.co", "spoti.fi"), "Spotify"),
        (("shopify.", "shopifycdn.", "myshopify."), "Shopify"),
        (("zoom.us", "zoom.com"), "Zoom"),
        (("dropbox.", "dropboxusercontent."), "Dropbox"),
        (("facebook.", "fbcdn.", "fb.com"), "Facebook"),
        (("instagram.", "cdninstagram."), "Instagram"),
        (("tiktok.", "musical.ly", "byteoversea."), "TikTok"),
        (("whatsapp.", "wa.me"), "WhatsApp"),
        (("speed.cloudflare.",), "speed.cloudflare.com"),
        (("wns.windows.com",), "Windows Notification"),
        (("microsoft.", "windowsupdate.", "office.com", "office.net", "live.com", "microsoftonline.", "cloudmessaging.edge.microsoft."), "Microsoft 365"),
        (("google.", "gstatic.", "googleapis."), "Google"),
        (("apple.com", "icloud.", "mzstatic."), "Apple"),
        (("twitter.", "x.com", "twimg."), "X / Twitter"),
        (("linkedin.",), "LinkedIn"),
        (("github.", "githubusercontent."), "GitHub"),
        (("whatsapp.",), "WhatsApp"),
    )
    _dns_cache: Dict[str, str] = {}

    def _is_cdn_label(self, name: Any) -> bool:
        return str(name or "").strip().lower() in self.CDN_LABELS

    def _clean_domain(self, value: Any) -> str:
        text = str(value or "").strip().lower().rstrip(".")
        if "://" in text:
            text = text.split("://", 1)[1]
        text = text.split("/")[0].split(":")[0]
        if text.startswith("www."):
            text = text[4:]
        if not text or self._looks_like_ip(text) or self._is_generic_app(text) or self._is_protocol_label(text):
            return ""
        if "." not in text:
            return ""
        return text

    def _is_cdn_domain(self, domain: str) -> bool:
        host = self._clean_domain(domain)
        # Solo el apex del CDN. speed.cloudflare.com SÍ es la página y hay que mostrarla.
        return host in self.CDN_DOMAINS

    def _app_from_domain(self, domain: str) -> str:
        host = self._clean_domain(domain)
        if not host or self._is_cdn_domain(host):
            return ""
        for needles, label in self.DOMAIN_APPS:
            if any(n in host for n in needles):
                return label
        return host

    def _domain_from_row(self, row: Dict[str, Any]) -> str:
        for key in ("resolved", "name", "domain", "webdomain", "hostname", "dstname", "url", "sni", "server_name"):
            domain = self._clean_domain(row.get(key))
            if domain:
                return domain
        return ""

    def _reverse_dns(self, ip: str) -> str:
        host = str(ip or "").split(":")[0]
        if not host or not self._looks_like_ip(host) or host in self._dns_cache:
            cached = self._dns_cache.get(host, "")
            return "" if self._is_cdn_domain(cached) else cached
        previous = socket.getdefaulttimeout()
        socket.setdefaulttimeout(0.7)
        try:
            name = socket.gethostbyaddr(host)[0]
        except Exception:
            name = ""
        finally:
            socket.setdefaulttimeout(previous)
        domain = self._clean_domain(name)
        self._dns_cache[host] = domain
        return "" if self._is_cdn_domain(domain) else domain

    def _app_from_dest(self, ip: str) -> str:
        # No adivinar app por rango CDN: 162.159.140.220 en Playa es speed.cloudflare.com, no Discord.
        return ""

    def _dest_label(self, ip: str, domain: str = "") -> str:
        if domain and not self._is_generic_app(domain) and not self._looks_like_ip(domain):
            return domain
        hinted = self._app_from_dest(ip)
        if hinted:
            return hinted
        return ""

    def _app_from_port(self, port: Any, proto: Any = "", named: str = "") -> str:
        named = str(named or "").strip()
        if named and not self._is_generic_app(named) and not self._looks_like_ip(named):
            return named.upper() if named.isalpha() else named
        try:
            p = int(port)
        except (TypeError, ValueError):
            p = 0
        proto_txt = str(proto).upper()
        mapping = {
            20: "FTP", 21: "FTP", 22: "SSH", 23: "TELNET", 25: "SMTP", 53: "DNS",
            67: "DHCP", 68: "DHCP", 80: "HTTP", 110: "POP3", 123: "NTP",
            135: "RPC", 139: "NETBIOS", 143: "IMAP", 161: "SNMP", 389: "LDAP",
            443: "HTTPS", 445: "SMB", 465: "SMTPS", 587: "SMTP", 636: "LDAPS",
            853: "DoT", 993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 3306: "MySQL",
            3389: "RDP", 5000: "UPnP", 5060: "SIP", 5222: "XMPP", 5353: "mDNS",
            8080: "HTTP", 8443: "HTTPS", 8530: "HTTP",
        }
        if p in mapping:
            return mapping[p]
        if proto_txt in ("1", "ICMP"):
            return "ICMP"
        if p:
            return f"{proto_txt or 'TCP'}/{p}"
        return ""

    def _app_from_row(self, row: Dict[str, Any], dstip: str = "") -> str:
        named = self._named_app(row)
        if named:
            return named
        _, dport = self._endpoint(row, "dstip", "dstaddr", "destination", "dst")
        port = row.get("dport") or row.get("dstport") or dport
        proto = row.get("proto") or row.get("protocol")
        from_port = self._app_from_port(port, proto, "")
        if from_port:
            return from_port
        hinted = self._app_from_dest(dstip or self._endpoint(row, "dstip", "dstaddr", "destination", "dst", "daddr")[0])
        if hinted and not self._is_cdn_label(hinted):
            return hinted
        return ""

    def _talker_key(self, row: Dict[str, Any], kind: str) -> str:
        if kind == "source":
            ip, _ = self._endpoint(row, "srcip", "srcaddr", "source", "src", "saddr", "addr", "ip")
            if ip:
                return ip
            name = row.get("name") or row.get("srcname")
            return str(name) if name else ""
        if kind == "destination":
            ip, _ = self._endpoint(row, "dstip", "dstaddr", "destination", "dst", "daddr", "addr", "ip")
            if ip:
                return ip
            name = row.get("name") or row.get("dstname")
            return str(name) if name else ""
        return self._app_from_row(row)

    def _aggregate_sessions(self, rows: List[Dict[str, Any]], kind: str, exclude_keys: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        exclude = set(exclude_keys or [])
        buckets: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            if kind == "source":
                key = row.get("srcip")
            elif kind == "destination":
                key = row.get("dstip")
            else:
                key = row.get("app")
            if not key or key in ("—", "-", "unknown", "Tráfico no clasificado"):
                continue
            key = str(key)
            if key in exclude:
                continue
            bucket = buckets.setdefault(key, {"key": key, "kind": kind, "sessions": 0, "bytes": 0})
            bucket["sessions"] += 1
            bucket["bytes"] += int(row.get("bytes") or 0)
        items = list(buckets.values())
        if kind == "destination":
            public = [i for i in items if self._looks_like_ip(i["key"]) and not self._is_private_ip(i["key"])]
            items = public or [i for i in items if i["key"] not in exclude]
        return sorted(items, key=lambda x: x["bytes"], reverse=True)[:12]

    def _apps_list_names(self, row: Dict[str, Any]) -> List[str]:
        names = []
        apps = row.get("apps")
        if isinstance(apps, list):
            for item in apps:
                if isinstance(item, dict) and item.get("name"):
                    names.append(str(item.get("name")))
                elif isinstance(item, str):
                    names.append(item)
        return names

    def _normalize_session(self, row: Dict[str, Any]) -> Dict[str, Any]:
        # FortiOS 8: saddr/daddr = cliente/destino. snaddr = NAT del firewall, no usarlo como origen.
        srcip, srcport = self._endpoint(row, "orgsrcip", "orgsrc", "saddr", "srcip", "srcaddr", "source", "src")
        dstip, dstport = self._endpoint(row, "orgdstip", "orgdst", "daddr", "dstip", "dstaddr", "destination", "dst")
        if srcip and srcip == row.get("snaddr") and row.get("saddr") and row.get("saddr") != srcip:
            srcip = str(row.get("saddr"))
        sport = row.get("sport") or row.get("srcport") or srcport
        dport = row.get("dport") or row.get("dstport") or dstport
        proto = row.get("proto") or row.get("protocol") or ""
        proto_map = {6: "TCP", 17: "UDP", 1: "ICMP", "6": "TCP", "17": "UDP", "1": "ICMP"}
        proto_name = proto_map.get(proto, proto) or "TCP"
        tx_bytes, rx_bytes = self._row_tx_rx(row)
        domain = self._domain_from_row(row)
        named = self._named_app(row)
        if not named:
            for app_name in self._apps_list_names(row):
                if not self._is_protocol_label(app_name) and "/" not in app_name and not self._looks_like_ip(app_name):
                    named = app_name
                    break
        app = named or self._app_from_domain(domain)
        if not app:
            port_app = self._app_from_port(row.get("dport") or row.get("dstport") or dport, proto, "")
            app = port_app
        return {
            "srcip": srcip,
            "dstip": dstip,
            "srcintf": row.get("srcintf") or row.get("source_interface") or "",
            "dstintf": row.get("dstintf") or row.get("destination_interface") or "",
            "sport": self._as_int(sport),
            "dport": self._as_int(dport),
            "proto": proto_name,
            "app": app,
            "bytes": tx_bytes + rx_bytes or self._row_bytes(row),
            "tx_bytes": tx_bytes,
            "rx_bytes": rx_bytes,
            "duration": self._as_int(row.get("duration") or row.get("seconds") or 0),
            "policy": row.get("policyid") or row.get("policy") or "",
            "user": row.get("username") or row.get("user") or "",
            "hostname": "",
            "dst_host": domain or self._dest_label(dstip),
            "tx_packets": self._as_int(row.get("tx_packets") or row.get("sentpkt") or 0),
            "rx_packets": self._as_int(row.get("rx_packets") or row.get("rcvdpkt") or 0),
            "country": row.get("country") or "",
            "nat_ip": row.get("snaddr") or row.get("transip") or "",
            "expiry": self._as_int(row.get("expiry") or 0),
        }

    def _looks_like_source_list(self, items: List[Dict[str, Any]]) -> bool:
        if not items:
            return True
        return all(self._looks_like_ip(i.get("key")) for i in items[:5])

    def _dns_names_by_source(self) -> Dict[str, List[str]]:
        buckets: Dict[str, List[str]] = {}
        for log in self.get_dns_logs(250):
            src, _ = self._endpoint(log, "srcip", "srcaddr", "src", "source")
            qname = self._clean_domain(log.get("qname") or log.get("hostname") or log.get("domain") or log.get("question"))
            if not src or not qname or self._is_cdn_domain(qname):
                continue
            names = buckets.setdefault(src, [])
            if qname not in names:
                names.append(qname)
        return buckets

    def _make_talker(
        self,
        srcip: str,
        host_map: Dict[str, str],
        dstip: str = "",
        domain: str = "",
        app: str = "",
        tx_bytes: int = 0,
        rx_bytes: int = 0,
        sessions: int = 1,
        duration: int = 0,
    ) -> Dict[str, Any]:
        domain = self._clean_domain(domain)
        if self._is_cdn_domain(domain):
            domain = ""
        if self._is_generic_app(app) or self._is_cdn_label(app) or self._looks_like_ip(app) or (domain and self._is_protocol_label(app)):
            app = self._app_from_domain(domain) or domain or dstip or "HTTPS"
        elif domain and self._app_from_domain(domain) and self._is_cdn_label(app):
            app = self._app_from_domain(domain)
        total = tx_bytes + rx_bytes
        return {
            "srcip": srcip,
            "dstip": dstip,
            "srcintf": "",
            "dstintf": "",
            "sport": 0,
            "dport": 0,
            "proto": "",
            "app": app,
            "bytes": total,
            "tx_bytes": tx_bytes,
            "rx_bytes": rx_bytes or (0 if tx_bytes else total),
            "duration": duration,
            "policy": "",
            "user": "",
            "hostname": host_map.get(srcip, ""),
            "sessions": sessions,
            "dst_host": domain or dstip,
        }

    def _expand_source_triads(self, sources: List[Dict[str, Any]], host_map: Dict[str, str], realtime: bool) -> List[Dict[str, Any]]:
        """Un host → varias filas (app/dominio). El CDN no se trata como aplicación."""
        dns_by_src = self._dns_names_by_source()
        logs = self.get_traffic_logs(rows=200)
        built: List[Dict[str, Any]] = []
        seen = set()

        def add_row(**kwargs):
            row = self._make_talker(host_map=host_map, **kwargs)
            key = (row["srcip"], row["app"], row["dst_host"] or row["dstip"])
            if key in seen or not row["srcip"]:
                return
            seen.add(key)
            built.append(row)

        for item in sources[:8]:
            src = item.get("key") or ""
            if not src:
                continue

            app_rows = []
            for report in ("app", "application", "cloud-application"):
                app_rows = self._fortiview_by_source(report, src, realtime)
                if app_rows:
                    break
            domain_rows = []
            for report in ("web-domain", "domain", "hostname"):
                domain_rows = self._fortiview_by_source(report, src, realtime)
                if domain_rows:
                    break
            dest_rows = self._fortiview_by_source("destination", src, realtime)

            for row in app_rows[:8]:
                app = self._app_from_row(row)
                if self._is_generic_app(app) or self._is_cdn_label(app) or self._looks_like_ip(app):
                    continue
                tx, rx = self._row_tx_rx(row)
                dest_ip, _ = self._endpoint(row, "dstip", "dstaddr", "destination", "dst", "addr")
                add_row(srcip=src, dstip=dest_ip, app=app, domain=self._domain_from_row(row), tx_bytes=tx, rx_bytes=rx, sessions=self._as_int(row.get("sessions") or 1))

            for row in domain_rows[:8]:
                domain = self._domain_from_row(row)
                if not domain:
                    continue
                tx, rx = self._row_tx_rx(row)
                dest_ip, _ = self._endpoint(row, "dstip", "dstaddr", "destination", "dst", "addr")
                add_row(srcip=src, dstip=dest_ip, domain=domain, app=self._app_from_domain(domain), tx_bytes=tx, rx_bytes=rx, sessions=self._as_int(row.get("sessions") or 1))

            for log in logs:
                parsed = self._normalize_session(log)
                if parsed.get("srcip") != src:
                    continue
                domain = self._clean_domain(log.get("hostname") or log.get("url") or log.get("sni") or parsed.get("dst_host"))
                app = parsed.get("app") if not self._is_cdn_label(parsed.get("app")) else ""
                add_row(
                    srcip=src,
                    dstip=parsed.get("dstip") or "",
                    domain=domain,
                    app=app,
                    tx_bytes=int(parsed.get("tx_bytes") or 0),
                    rx_bytes=int(parsed.get("rx_bytes") or 0),
                    duration=int(parsed.get("duration") or 0),
                )

            for qname in (dns_by_src.get(src) or [])[:8]:
                add_row(srcip=src, domain=qname, app=self._app_from_domain(qname), rx_bytes=0)

            if not any(r["srcip"] == src for r in built):
                for row in dest_rows[:6]:
                    dest_ip = self._talker_key(row, "destination")
                    if not dest_ip:
                        continue
                    domain = self._reverse_dns(dest_ip)
                    tx, rx = self._row_tx_rx(row)
                    add_row(srcip=src, dstip=dest_ip, domain=domain, app=self._app_from_domain(domain), tx_bytes=tx, rx_bytes=rx, sessions=self._as_int(row.get("sessions") or 1))

        return built

    def _firewall_ips(self) -> Set[str]:
        ips = {self.ip}
        interfaces = self._as_list(self._request("/system/interface", is_cmdb=True, timeout=6))
        for iface in interfaces:
            raw_ip = str(iface.get("ip") or "").split()[0]
            if self._looks_like_ip(raw_ip) and raw_ip not in ("0.0.0.0", "127.0.0.1"):
                ips.add(raw_ip)
        return ips

    def _is_self_ip(self, ip: str, self_ips: Set[str]) -> bool:
        host = str(ip or "").split(":")[0]
        return bool(host) and host in self_ips

    def _is_noise_session(self, session: Dict[str, Any]) -> bool:
        bytes_ = int(session.get("bytes") or 0)
        if bytes_ >= 1_000_000:
            return False
        app = str(session.get("app") or "").lower()
        dport = int(session.get("dport") or 0)
        if app in self.NOISE_APPS or dport in self.NOISE_PORTS:
            return True
        dst = str(session.get("dstip") or "")
        if bytes_ < 8192 and self._is_private_ip(dst):
            return True
        return False

    def _is_lan_client(self, ip: str, self_ips: Set[str]) -> bool:
        host = str(ip or "").split(":")[0]
        return bool(host) and self._looks_like_ip(host) and self._is_private_ip(host) and host not in self_ips

    def _label_talker(self, session: Dict[str, Any]) -> None:
        domain = self._clean_domain(session.get("dst_host"))
        if domain:
            session["dst_host"] = domain
        app = session.get("app") or ""
        if domain and (self._is_protocol_label(app) or self._is_generic_app(app) or self._is_cdn_label(app)):
            session["app"] = self._app_from_domain(domain) or domain
        elif self._is_generic_app(app) or self._is_cdn_label(app):
            session["app"] = domain or session.get("dstip") or "HTTPS"

    def _talkers_from_rows(
        self,
        rows: List[Dict[str, Any]],
        host_map: Dict[str, str],
        self_ips: Set[str],
        keep_noise: bool = False,
    ) -> List[Dict[str, Any]]:
        buckets: Dict[tuple, Dict[str, Any]] = {}
        for row in rows:
            parsed = dict(row) if row.get("srcip") or row.get("dstip") else self._normalize_session(row)
            src = parsed.get("srcip") or ""
            dst = parsed.get("dstip") or ""
            if self._is_self_ip(src, self_ips):
                continue
            if not self._is_lan_client(src, self_ips):
                continue
            if not keep_noise and self._is_noise_session(parsed):
                continue
            domain = self._clean_domain(parsed.get("dst_host"))
            if not domain:
                domain = self._clean_domain(row.get("resolved") or row.get("url") or row.get("sni") or row.get("dstname"))
            if domain:
                parsed["dst_host"] = domain
            self._label_talker(parsed)
            app = parsed.get("app") or domain or dst or "HTTPS"
            dest_key = domain or dst
            key = (src, app, dest_key)
            bucket = buckets.get(key)
            if not bucket:
                bucket = self._make_talker(
                    srcip=src,
                    host_map=host_map,
                    dstip=dst,
                    domain=domain,
                    app=app,
                    tx_bytes=int(parsed.get("tx_bytes") or 0),
                    rx_bytes=int(parsed.get("rx_bytes") or 0),
                    sessions=1,
                    duration=int(parsed.get("duration") or 0),
                )
                bucket["sport"] = parsed.get("sport") or 0
                bucket["dport"] = parsed.get("dport") or 0
                bucket["proto"] = parsed.get("proto") or ""
                bucket["user"] = parsed.get("user") or ""
                bucket["srcintf"] = parsed.get("srcintf") or ""
                bucket["dstintf"] = parsed.get("dstintf") or ""
                bucket["country"] = parsed.get("country") or ""
                bucket["nat_ip"] = parsed.get("nat_ip") or ""
                bucket["tx_packets"] = int(parsed.get("tx_packets") or 0)
                bucket["rx_packets"] = int(parsed.get("rx_packets") or 0)
                bucket["policy"] = parsed.get("policy") or ""
                buckets[key] = bucket
                continue
            bucket["tx_bytes"] += int(parsed.get("tx_bytes") or 0)
            bucket["rx_bytes"] += int(parsed.get("rx_bytes") or 0)
            bucket["bytes"] = bucket["tx_bytes"] + bucket["rx_bytes"]
            bucket["sessions"] = int(bucket.get("sessions") or 1) + 1
            bucket["duration"] = max(int(bucket.get("duration") or 0), int(parsed.get("duration") or 0))
            if dst and (not bucket.get("dstip") or self._is_private_ip(bucket.get("dstip"))):
                bucket["dstip"] = dst
        return sorted(buckets.values(), key=lambda x: int(x.get("bytes") or 0), reverse=True)

    def get_traffic_audit(self, realtime: bool = True, start: Optional[int] = None, end: Optional[int] = None, srcip: Optional[str] = None) -> Dict[str, Any]:
        cache_key = f"{self.ip}|{int(bool(realtime))}|{srcip or ''}|{start or ''}|{end or ''}"
        now = time.time()
        with _AUDIT_LOCK:
            cached = _AUDIT_CACHE.get(cache_key)
            if cached and now - cached["ts"] < _AUDIT_TTL_SECONDS:
                return cached["data"]

        leases = self._request("/system/dhcp", timeout=6)
        if not isinstance(leases, list):
            leases = []
        host_map = {}
        for lease in leases:
            if isinstance(lease, dict) and lease.get("ip"):
                host_map[lease["ip"]] = lease.get("hostname") or ""

        self_ips = {self.ip}
        with ThreadPoolExecutor(max_workers=3) as pool:
            fut_sessions = pool.submit(self.get_sessions, 500)
            fut_fv_dest = pool.submit(self._fortiview, "destination", realtime, start, end, 30)
            raw_sessions = fut_sessions.result()
            fv_dests = fut_fv_dest.result() or []

        resolved_by_dst: Dict[str, str] = {}
        for row in fv_dests:
            dst = str(row.get("dstaddr") or row.get("daddr") or row.get("dstip") or "")
            domain = self._clean_domain(row.get("resolved") or row.get("hostname") or row.get("name"))
            if dst and domain:
                resolved_by_dst[dst] = domain

        parsed_sessions = []
        for raw in raw_sessions:
            parsed = self._normalize_session(raw)
            dst = parsed.get("dstip") or ""
            if dst in resolved_by_dst:
                parsed["dst_host"] = resolved_by_dst[dst]
            if parsed.get("srcip") or parsed.get("dstip"):
                parsed["hostname"] = host_map.get(parsed.get("srcip"), "")
                parsed_sessions.append(parsed)

        parsed_logs = []
        if not any(self._is_lan_client(s.get("srcip") or "", self_ips) for s in parsed_sessions):
            raw_logs = self.get_traffic_logs(start, end, 180)
            for log in raw_logs:
                parsed = self._normalize_session(log)
                domain = self._clean_domain(log.get("hostname") or log.get("url") or log.get("sni") or log.get("dstname"))
                if domain:
                    parsed["dst_host"] = domain
                dst = parsed.get("dstip") or ""
                if dst in resolved_by_dst:
                    parsed["dst_host"] = resolved_by_dst[dst]
                if parsed.get("srcip") or parsed.get("dstip"):
                    parsed["hostname"] = host_map.get(parsed.get("srcip"), "")
                    parsed_logs.append(parsed)

        if srcip:
            parsed_sessions = [s for s in parsed_sessions if s["srcip"] == srcip or s["dstip"] == srcip]
            parsed_logs = [s for s in parsed_logs if s["srcip"] == srcip or s["dstip"] == srcip]

        talkers = self._talkers_from_rows(parsed_sessions, host_map, self_ips)
        log_talkers = self._talkers_from_rows(parsed_logs, host_map, self_ips)
        if not talkers:
            talkers = log_talkers
        elif log_talkers:
            by_src_dst = {(t["srcip"], t.get("dstip") or t.get("dst_host")): t for t in talkers}
            by_src_app = {(t["srcip"], t["app"]): t for t in talkers}
            for extra in log_talkers:
                dest = extra.get("dstip") or extra.get("dst_host")
                current = by_src_dst.get((extra["srcip"], dest)) or by_src_app.get((extra["srcip"], extra["app"]))
                if current and (self._is_protocol_label(current.get("app")) or not self._clean_domain(current.get("dst_host"))):
                    if extra.get("dst_host"):
                        current["dst_host"] = extra["dst_host"]
                    if extra.get("app"):
                        current["app"] = extra["app"]
                    current["dstip"] = extra.get("dstip") or current.get("dstip")
                    current["tx_bytes"] = max(int(current.get("tx_bytes") or 0), int(extra.get("tx_bytes") or 0))
                    current["rx_bytes"] = max(int(current.get("rx_bytes") or 0), int(extra.get("rx_bytes") or 0))
                    current["bytes"] = current["tx_bytes"] + current["rx_bytes"]
                    self._label_talker(current)
                    continue
                if not current:
                    talkers.append(extra)
                    by_src_app[(extra["srcip"], extra["app"])] = extra
                    by_src_dst[(extra["srcip"], dest)] = extra

        if not talkers:
            fv_sources = []
            for row in self._fortiview("source", realtime, start, end, count=20):
                key = self._talker_key(row, "source")
                if not key or self._is_self_ip(key, self_ips) or not self._is_lan_client(key, self_ips):
                    continue
                fv_sources.append(row)
            talkers = self._talkers_from_rows(
                [
                    {
                        **self._normalize_session(row),
                        "srcip": self._talker_key(row, "source"),
                        "hostname": host_map.get(self._talker_key(row, "source"), ""),
                    }
                    for row in fv_sources
                ],
                host_map,
                self_ips,
                keep_noise=True,
            )
            if talkers:
                # Sin logs/sesiones útiles: una fila por host LAN, no inventar apps globales.
                pass

        talkers = [t for t in talkers if not self._is_self_ip(t.get("srcip"), self_ips)]
        named_by_src = {}
        for t in talkers:
            if not self._is_protocol_label(t.get("app")):
                named_by_src.setdefault(t.get("srcip"), []).append(t)
        cleaned = []
        for t in talkers:
            src = t.get("srcip")
            if self._is_protocol_label(t.get("app")) and src in named_by_src:
                named_bytes = max(int(x.get("bytes") or 0) for x in named_by_src[src])
                if int(t.get("bytes") or 0) <= max(named_bytes * 1.2, 1):
                    continue
            cleaned.append(t)
        talkers = cleaned
        for session in talkers:
            session["hostname"] = host_map.get(session.get("srcip"), session.get("hostname") or "")
            self._label_talker(session)
        talkers = sorted(talkers, key=lambda x: int(x.get("bytes") or 0), reverse=True)[:60]

        source_keys = {s["srcip"] for s in talkers if s.get("srcip")}
        sources = self._aggregate_sessions(talkers, "source")
        applications = self._aggregate_sessions(talkers, "application")
        destinations = self._aggregate_sessions(talkers, "destination", exclude_keys=list(source_keys) + list(self_ips))

        def enrich(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            for item in items:
                item["hostname"] = host_map.get(item.get("key"), "")
            return items[:12]

        data_source = "sessions+logs" if parsed_sessions and parsed_logs else ("logs" if parsed_logs else "sessions")
        payload = {
            "mode": "realtime" if realtime else "historical",
            "source": data_source,
            "sources": enrich(sources),
            "applications": enrich(applications),
            "destinations": enrich(destinations),
            "sessions": talkers,
            "session_count": len(talkers),
            "generated_at": int(now),
            "cached": False,
        }
        with _AUDIT_LOCK:
            _AUDIT_CACHE[cache_key] = {"ts": now, "data": {**payload, "cached": True}}
        return payload

    def _matches_talker(self, session: Dict[str, Any], srcip: str, dstip: Optional[str], dst_host: Optional[str]) -> bool:
        if session.get("srcip") != srcip:
            return False
        targets = {x for x in (dstip, dst_host) if x}
        if not targets:
            return True
        return session.get("dstip") in targets or session.get("dst_host") in targets

    def get_session_detail(self, srcip: str, dstip: Optional[str] = None, dst_host: Optional[str] = None) -> Dict[str, Any]:
        """Detalle de una conversación src → dest: sesiones vivas, página, tiempos y curva de consumo."""
        now = int(time.time())
        leases = self._request("/system/dhcp", timeout=5)
        host_map = {}
        for lease in leases if isinstance(leases, list) else []:
            if isinstance(lease, dict) and lease.get("ip"):
                host_map[lease["ip"]] = lease.get("hostname") or ""

        resolved_by_dst: Dict[str, str] = {}
        fv_row = {}
        for row in self._fortiview("destination", True, None, None, 30):
            dest = str(row.get("dstaddr") or row.get("daddr") or row.get("dstip") or "")
            domain = self._clean_domain(row.get("resolved") or row.get("hostname"))
            if dest and domain:
                resolved_by_dst[dest] = domain
            src = str(row.get("srcaddr") or row.get("saddr") or row.get("srcip") or "")
            wanted = {x for x in (dstip, dst_host) if x}
            if src == srcip and dest and (dest in wanted or (domain and domain in wanted)):
                fv_row = row

        matches = []
        for raw in self.get_sessions(500):
            parsed = self._normalize_session(raw)
            dest = parsed.get("dstip") or ""
            if dest in resolved_by_dst:
                parsed["dst_host"] = resolved_by_dst[dest]
            parsed["hostname"] = host_map.get(parsed.get("srcip"), "")
            if self._matches_talker(parsed, srcip, dstip, dst_host):
                matches.append(parsed)

        if not matches:
            for log in self.get_traffic_logs(rows=80):
                parsed = self._normalize_session(log)
                domain = self._clean_domain(log.get("hostname") or log.get("url") or log.get("sni") or log.get("resolved"))
                if domain:
                    parsed["dst_host"] = domain
                parsed["hostname"] = host_map.get(parsed.get("srcip"), "")
                if self._matches_talker(parsed, srcip, dstip, dst_host):
                    parsed["from_log"] = True
                    matches.append(parsed)

        tx = sum(int(s.get("tx_bytes") or 0) for s in matches)
        rx = sum(int(s.get("rx_bytes") or 0) for s in matches)
        if not tx and not rx and fv_row:
            tx = self._as_int(fv_row.get("sentbyte"))
            rx = self._as_int(fv_row.get("rcvdbyte"))
        tx_pkts = sum(int(s.get("tx_packets") or 0) for s in matches) or self._as_int(fv_row.get("tx_packets"))
        rx_pkts = sum(int(s.get("rx_packets") or 0) for s in matches) or self._as_int(fv_row.get("rx_packets"))
        duration = max((int(s.get("duration") or 0) for s in matches), default=0)
        primary = max(matches, key=lambda s: int(s.get("bytes") or 0), default={})
        dest_ip = primary.get("dstip") or dstip or ""
        page = primary.get("dst_host") or resolved_by_dst.get(dest_ip) or dst_host or dest_ip
        app = primary.get("app") or self._app_from_domain(page) or page
        if page and (self._is_protocol_label(app) or self._is_generic_app(app)):
            app = self._app_from_domain(page) or page
        active = any(not s.get("from_log") for s in matches)
        started_at = now - duration if duration else now
        ended_at = None if active else now
        total = tx + rx
        rate_bps = int(total * 8 / duration) if duration else 0

        points = 24
        series = []
        span = max(duration, 1)
        for i in range(points + 1):
            frac = i / points
            series.append({
                "t": started_at + int(span * frac),
                "tx": int(tx * frac),
                "rx": int(rx * frac),
            })

        host = host_map.get(srcip) or primary.get("hostname") or srcip
        verb = "sigue" if active else "tuvo"
        story = (
            f"{host} ({srcip}) {verb} una sesión {str(primary.get('proto') or 'TCP').upper()}"
            f"{('/' + str(primary.get('dport'))) if primary.get('dport') else ''} hacia "
            f"{page}{f' ({dest_ip})' if dest_ip and dest_ip != page else ''}. "
            f"Ha enviado {tx} bytes y recibido {rx} bytes"
            f"{f' en {duration} s' if duration else ''}."
        )
        if active:
            story += " La sesión sigue abierta en la tabla del FortiGate."
        else:
            story += " Ya no aparece en la tabla de sesiones vivas."

        return {
            "srcip": srcip,
            "hostname": host,
            "dstip": dest_ip,
            "dst_host": page,
            "app": app,
            "proto": primary.get("proto") or "",
            "sport": primary.get("sport") or 0,
            "dport": primary.get("dport") or 0,
            "srcintf": primary.get("srcintf") or "",
            "dstintf": primary.get("dstintf") or "",
            "country": primary.get("country") or fv_row.get("country") or "",
            "nat_ip": primary.get("nat_ip") or "",
            "policy": primary.get("policy") or "",
            "tx_bytes": tx,
            "rx_bytes": rx,
            "bytes": total,
            "tx_packets": tx_pkts,
            "rx_packets": rx_pkts,
            "tx_bandwidth": self._as_int(fv_row.get("tx_bandwidth")),
            "rx_bandwidth": self._as_int(fv_row.get("rx_bandwidth")),
            "duration": duration,
            "started_at": started_at,
            "ended_at": ended_at,
            "now": now,
            "active": active,
            "rate_bps": rate_bps,
            "session_count": len(matches),
            "sessions": matches[:20],
            "series": series,
            "series_note": "Curva acumulada a partir de la duración y los bytes actuales. FortiOS no entrega muestras intermedias de esta sesión.",
            "story": story,
        }
