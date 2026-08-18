import httpx
import logging
import time

logger = logging.getLogger(__name__)

class ZabbixService:
    # Tokens de desglose de CPU. Si se mezclan con system.cpu.util agregada,
    # la gráfica salta de ~0 a ~100 (idle) en cada muestra.
    _CPU_BREAKDOWN = (
        "idle", "user", "system", "iowait", "nice", "steal",
        "guest", "interrupt", "softirq", "kernel"
    )

    def __init__(self, url: str = "http://192.168.20.4/api_jsonrpc.php", username: str = "Admin", password: str = "zabbix"):
        self.url = url
        self.username = username
        self.password = password
        self.auth_token = None

    @classmethod
    def _cpu_item_score(cls, key: str) -> int:
        """Mayor puntaje = utilización agregada. Negativo = descartar (idle/user/...)."""
        k = (key or "").lower()
        if not k.startswith("system.cpu.util"):
            return -1
        params = ""
        if "[" in k:
            close = k.find("]", k.find("["))
            params = k[k.find("[") + 1: close if close != -1 else None]
        if any(token in params for token in cls._CPU_BREAKDOWN):
            return -1
        if k in ("system.cpu.util", "system.cpu.util[]"):
            return 100
        if "avg" in k:
            return 80
        return 50

    @staticmethod
    def _parse_numeric(raw):
        if raw is None or raw == "":
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    async def _authenticate(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {"username": self.username, "password": self.password},
            "id": 1
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                if "error" in data:
                    raise Exception(f"Zabbix auth error: {data['error'].get('data')}")
                self.auth_token = data.get("result")
                return self.auth_token
            except Exception as e:
                logger.error(f"Fallo al conectar con la API de Zabbix: {str(e)}")
                raise

    async def get_dashboard_summary(self):
        if not self.auth_token:
            await self._authenticate()
        
        async with httpx.AsyncClient() as client:
            # Get Total and Online servers
            payload_hosts = {
                "jsonrpc": "2.0", "method": "host.get",
                "params": {"output": ["hostid", "available"], "filter": {"status": "0"}},
                "auth": self.auth_token, "id": 1
            }
            resp_hosts = await client.post(self.url, json=payload_hosts, timeout=10.0)
            hosts = resp_hosts.json().get("result", [])
            total_servers = len(hosts)
            online_servers = sum(1 for h in hosts if h.get("available") == "1")

            # Get Critical Problems
            payload_probs = {
                "jsonrpc": "2.0", "method": "problem.get",
                "params": {"output": ["problemid"], "severities": [4, 5]},
                "auth": self.auth_token, "id": 2
            }
            resp_probs = await client.post(self.url, json=payload_probs, timeout=10.0)
            probs = resp_probs.json().get("result", [])
            critical_problems = len(probs)

            return {
                "total_servers": total_servers,
                "online": online_servers,
                "critical_problems": critical_problems
            }

    async def get_all_hosts(self, time_from: int = None, time_till: int = None):
        if not self.auth_token:
            await self._authenticate()
        
        current_time = int(time.time())
        time_from = time_from if time_from else current_time - 3600
        time_till = time_till if time_till else current_time
            
        payload_hosts = {
            "jsonrpc": "2.0", "method": "host.get",
            "params": {
                "output": ["hostid", "host", "name", "available"],
                "selectInterfaces": ["ip"],
                "selectInventory": ["os", "os_full"],
                "filter": {"status": "0"}
            },
            "auth": self.auth_token, "id": 2
        }
        
        async with httpx.AsyncClient() as client:
            resp_hosts = await client.post(self.url, json=payload_hosts, timeout=15.0)
            hosts = resp_hosts.json().get("result", [])
            
            host_map = {}
            for h in hosts:
                ip = h["interfaces"][0]["ip"] if h.get("interfaces") else "N/A"
                status_id = h.get("available", "0")
                # Zabbix: 1=Available (Online/verde), 2=Unavailable (Offline/rojo), 0=Unknown (Warning/amarillo)
                # Default a Online a menos que el agente esté explícitamente caído (2)
                status_text = "Offline" if status_id == "2" else "Online"
                
                # Fetch OS from inventory, or infer from name
                os_name = "Desconocido"
                if h.get("inventory") and isinstance(h["inventory"], dict):
                    os_name = h["inventory"].get("os") or h["inventory"].get("os_full") or "Desconocido"
                if os_name == "Desconocido":
                    if "WIN" in h["name"].upper(): os_name = "Windows"
                    elif "LNX" in h["name"].upper() or "LINUX" in h["name"].upper(): os_name = "Linux"

                host_map[h["hostid"]] = {
                    "hostid": h["hostid"],
                    "hostname": h["name"],
                    "ip": ip,
                    "os": os_name,
                    "status": status_text,
                    "cpu": 0, "ram": 0,
                    "sessions": 0, "vpn_tunnels": 0, "net_in": 0, "net_out": 0,
                    "last_polled_clock": 0,
                    "cpu_history": [], "ram_history": [],
                    "sessions_history": [], "net_in_history": [], "net_out_history": []
                }
            
            if not host_map:
                return []
            
            payload_items = {
                "jsonrpc": "2.0", "method": "item.get",
                "params": {
                    "output": ["itemid", "hostid", "name", "key_", "lastvalue", "value_type", "lastclock"],
                    "hostids": list(host_map.keys()),
                    "search": {"key_": ["system.cpu.util", "vm.memory.util", "vm.memory.size", "fortignw.sessions", "vpn", "ipsec", "net.if.in", "net.if.out"]},
                    "searchByAny": True
                },
                "auth": self.auth_token, "id": 3
            }
            resp_items = await client.post(self.url, json=payload_items, timeout=15.0)
            items = resp_items.json().get("result", [])
            
            mem_cache = {}
            item_id_map = {}
            cpu_choice = {}
            ram_choice = {}
            
            now = int(time.time())
            
            for item in items:
                hid = item["hostid"]
                key = item["key_"]
                val = self._parse_numeric(item.get("lastvalue"))
                clock = int(item.get("lastclock") or 0)
                
                # If data is stale (> 3 mins), ignore the value so it drops to 0 or null
                if clock and (now - clock) > 180:
                    val = None
                    
                cpu_score = self._cpu_item_score(key)
                
                is_polled = False
                if cpu_score > 0:
                    is_polled = True
                elif "net.if.in" in key or "net.if.out" in key:
                    is_polled = True
                elif "fortignw.sessions" in key or "sessions" in item.get("name", "").lower():
                    is_polled = True
                    
                if is_polled and clock > host_map[hid]["last_polled_clock"]:
                    host_map[hid]["last_polled_clock"] = clock

                if cpu_score > 0 and val is not None:
                    prev = cpu_choice.get(hid)
                    if not prev or cpu_score > prev[0]:
                        cpu_choice[hid] = (cpu_score, item["itemid"], val, item.get("value_type", "0"))
                elif "vm.memory.util" in key or key == "vm.memory.size[pused]":
                    if val is not None and hid not in ram_choice:
                        ram_choice[hid] = (item["itemid"], val, item.get("value_type", "0"))
                elif key in ["vm.memory.size[used]", "vm.memory.size[total]"]:
                    if hid not in mem_cache:
                        mem_cache[hid] = {}
                    parsed = val if val is not None else 0.0
                    mem_cache[hid]["used" if "used" in key else "total"] = parsed
                elif "fortignw.sessions" in key or "sessions" in item.get("name", "").lower():
                    if val is not None:
                        host_map[hid]["sessions"] = int(val)
                        item_id_map[item["itemid"]] = {"hostid": hid, "type": "sessions"}
                elif "vpn" in key.lower() or "ipsec" in key.lower() or "tunnel" in key.lower():
                    if val is not None and "status" not in key.lower():
                        host_map[hid]["vpn_tunnels"] += int(val) # Sum up all tunnels if there are multiple items
                elif "net.if.in" in key:
                    if val is not None:
                        host_map[hid]["net_in"] += round(val, 2)
                        item_id_map[item["itemid"]] = {"hostid": hid, "type": "net_in", "val_type": item["value_type"]}
                elif "net.if.out" in key:
                    if val is not None:
                        host_map[hid]["net_out"] += round(val, 2)
                        item_id_map[item["itemid"]] = {"hostid": hid, "type": "net_out", "val_type": item["value_type"]}

            for hid, (_, iid, val, vtype) in cpu_choice.items():
                host_map[hid]["cpu"] = round(val, 2)
                item_id_map[iid] = {"hostid": hid, "type": "cpu", "val_type": vtype}

            for hid, (iid, val, vtype) in ram_choice.items():
                host_map[hid]["ram"] = round(val, 2)
                item_id_map[iid] = {"hostid": hid, "type": "ram", "val_type": vtype}
            
            for hid, mem in mem_cache.items():
                if host_map[hid]["ram"] == 0 and "used" in mem and "total" in mem and mem["total"] > 0:
                    host_map[hid]["ram"] = round((mem["used"] / mem["total"]) * 100, 2)
            
            async def fetch_history(item_ids, value_type):
                if not item_ids: return []
                req = {
                    "jsonrpc": "2.0", "method": "history.get",
                    "params": {
                        "output": ["itemid", "clock", "value"],
                        "history": value_type,
                        "itemids": item_ids,
                        "time_from": time_from,
                        "time_till": time_till,
                        "sortfield": "clock",
                        "sortorder": "ASC"
                    },
                    "auth": self.auth_token, "id": 4
                }
                res = await client.post(self.url, json=req, timeout=20.0)
                return res.json().get("result", [])

            float_items = []
            uint_items = []
            for iid, data in item_id_map.items():
                vt = str(data.get("val_type", ""))
                if vt == "3":
                    uint_items.append(iid)
                elif vt == "0":
                    float_items.append(iid)
                else:
                    if data["type"] in ["cpu", "ram"]: float_items.append(iid)
                    else: uint_items.append(iid)
            
            history_data = await fetch_history(float_items, 0)
            if uint_items:
                history_data += await fetch_history(uint_items, 3)
            
            for h in history_data:
                iid = h["itemid"]
                if iid not in item_id_map:
                    continue
                val = self._parse_numeric(h.get("value"))
                if val is None:
                    continue
                hid = item_id_map[iid]["hostid"]
                t_type = item_id_map[iid]["type"]
                # Para redes con múltiples interfaces, esto sumará el historial si coinciden en timestamp,
                # pero para propósitos del top chart en modo Firewall, anexaremos la historia y la agruparemos.
                host_map[hid][f"{t_type}_history"].append([int(h["clock"]) * 1000, round(val, 2)])
            
            # Fetch active triggers (problems) to override status
            payload_probs = {
                "jsonrpc": "2.0", "method": "trigger.get",
                "params": {
                    "output": ["priority", "description"],
                    "selectHosts": ["hostid"],
                    "hostids": list(host_map.keys()),
                    "filter": {"value": "1"}, # 1 = Problem state
                    "skipDependent": True,
                    "active": True
                },
                "auth": self.auth_token, "id": 5
            }
            resp_probs = await client.post(self.url, json=payload_probs, timeout=10.0)
            triggers = resp_probs.json().get("result", [])
            for t in triggers:
                sev = int(t.get("priority", 0))
                desc = t.get("description", "").lower()
                is_unavailable = any(kw in desc for kw in ["not available", "unavailable", "down", "unreachable"])
                
                for h in t.get("hosts", []):
                    hid = h["hostid"]
                    if hid in host_map:
                        if sev >= 4 or is_unavailable:
                            host_map[hid]["status"] = "Offline"
                        elif sev >= 2 and host_map[hid]["status"] != "Offline":
                            host_map[hid]["status"] = "Warning"
                            
            current_time = int(time.time())
            for hid, h in host_map.items():
                lpc = h.get("last_polled_clock", 0)
                # Zabbix agent sends data every 60s. We set timeout to 75s (15s tolerance).
                if lpc > 0 and current_time - lpc > 75:
                    h["status"] = "Offline"
                            
            # Enforce Offline status if last_polled_clock is completely stale (> 3 mins) or never updated
            for hid, h in host_map.items():
                if h["last_polled_clock"] > 0 and (now - h["last_polled_clock"]) > 180:
                    h["status"] = "Offline"
                elif h["last_polled_clock"] == 0:
                    h["status"] = "Offline"
            
            return list(host_map.values())

    async def get_host_detail(self, host_id_or_name: str):
        if not self.auth_token:
            await self._authenticate()
            
        search_keys = [
            "system.cpu.util", "vm.memory.util", "vm.memory.size",
            "vfs.fs.size", "vfs.fs.dependent.size", "perf_counter", "system.uptime", 
            "net.if.in", "net.if.out", "fortignw.sessions", "active sessions"
        ]
        param_filter = {"hostids": host_id_or_name} if host_id_or_name.isdigit() else {"host": host_id_or_name}
        
        async with httpx.AsyncClient() as client:
            payload = {
                "jsonrpc": "2.0", "method": "item.get",
                "params": {
                    "output": ["itemid", "name", "key_", "lastvalue", "units", "value_type"],
                    **param_filter,
                    "search": {"key_": search_keys},
                    "searchByAny": True
                },
                "auth": self.auth_token, "id": 5
            }
            resp = await client.post(self.url, json=payload, timeout=15.0)
            items = resp.json().get("result", [])
            
            metrics = {
                "cpu": {"value": 0, "history": []},
                "ram": {"value": 0, "history": []},
                "disks": [],
                "interfaces": {}, # { "iface_name": { "in": {value, history}, "out": {value, history} } }
                "latency": {"value": 0, "history": []},
                "sessions": {"value": None, "history": []},
                "uptime": 0
            }
            
            mem_total, mem_used = 0.0, 0.0
            item_id_map = {}
            best_cpu = None
            
            for item in items:
                key = item.get("key_", "")
                val = self._parse_numeric(item.get("lastvalue"))
                    
                cpu_score = self._cpu_item_score(key)
                if cpu_score > 0 and val is not None:
                    if not best_cpu or cpu_score > best_cpu[0]:
                        best_cpu = (cpu_score, item["itemid"], val)
                elif "vm.memory.util" in key or "vm.memory.size[pused]" in key:
                    if val is not None and "ram" not in [d.get("type") for d in item_id_map.values()]:
                        metrics["ram"]["value"] = round(val, 2)
                        item_id_map[item["itemid"]] = {"type": "ram"}

            if best_cpu:
                metrics["cpu"]["value"] = round(best_cpu[2], 2)
                item_id_map[best_cpu[1]] = {"type": "cpu"}

            for item in items:
                key = item.get("key_", "")
                val = self._parse_numeric(item.get("lastvalue"))
                if val is None:
                    val = 0.0
                elif key == "vm.memory.size[total]": mem_total = val
                elif key == "vm.memory.size[used]": mem_used = val
                elif ("vfs.fs.size" in key or "vfs.fs.dependent.size" in key) and "pused" in key:
                    disk_name = key.split("[")[1].split(",")[0]
                    metrics["disks"].append({"name": disk_name, "value": round(val, 2)})
                elif "system.uptime" in key:
                    metrics["uptime"] = int(val)
                elif "net.if.in" in key:
                    raw_name = item.get("name", "")
                    iface = raw_name.split(':')[0].strip() if ':' in raw_name else raw_name
                    if not iface: iface = "Unknown"
                    if iface not in metrics["interfaces"]:
                        metrics["interfaces"][iface] = {"in": {"value": 0, "history": []}, "out": {"value": 0, "history": []}}
                    metrics["interfaces"][iface]["in"]["value"] = round(val, 2)
                    item_id_map[item["itemid"]] = {"type": "net_in", "val_type": item["value_type"], "iface": iface}
                elif "net.if.out" in key:
                    raw_name = item.get("name", "")
                    iface = raw_name.split(':')[0].strip() if ':' in raw_name else raw_name
                    if not iface: iface = "Unknown"
                    if iface not in metrics["interfaces"]:
                        metrics["interfaces"][iface] = {"in": {"value": 0, "history": []}, "out": {"value": 0, "history": []}}
                    metrics["interfaces"][iface]["out"]["value"] = round(val, 2)
                    item_id_map[item["itemid"]] = {"type": "net_out", "val_type": item["value_type"], "iface": iface}
                elif "fortignw.sessions" in key or "sessions" in item.get("name", "").lower():
                    metrics["sessions"]["value"] = int(val)
                    item_id_map[item["itemid"]] = {"type": "sessions", "val_type": item["value_type"]}
                elif "perf_counter" in key and "Current Disk Queue Length" in key:
                    metrics["latency"]["value"] = round(val, 2)
                    item_id_map[item["itemid"]] = {"type": "latency", "val_type": item["value_type"]}
            
            if metrics["ram"]["value"] == 0 and mem_total > 0:
                metrics["ram"]["value"] = round((mem_used / mem_total) * 100, 2)

            time_from = int(time.time()) - 3600
            async def fetch_hist(itemids, vtype):
                if not itemids: return []
                req = {
                    "jsonrpc": "2.0", "method": "history.get",
                    "params": {
                        "output": ["itemid", "clock", "value"],
                        "history": vtype,
                        "itemids": itemids,
                        "time_from": time_from,
                        "sortfield": "clock", "sortorder": "ASC"
                    },
                    "auth": self.auth_token, "id": 6
                }
                res = await client.post(self.url, json=req, timeout=20.0)
                return res.json().get("result", [])

            float_items = [iid for iid, d in item_id_map.items() if d.get("val_type", "0") == "0"]
            uint_items = [iid for iid, d in item_id_map.items() if d.get("val_type") == "3"]

            history_data = await fetch_hist(float_items, 0) + await fetch_hist(uint_items, 3)

            for h in history_data:
                iid = h["itemid"]
                if iid not in item_id_map: continue
                val = self._parse_numeric(h.get("value"))
                if val is None: continue
                
                t = item_id_map[iid]["type"]
                clock_ms = int(h["clock"]) * 1000
                if t in ["cpu", "ram", "latency", "sessions"]:
                    metrics[t]["history"].append([clock_ms, round(val, 2)])
                elif t in ["net_in", "net_out"]:
                    iface = item_id_map[iid]["iface"]
                    sub = "in" if t == "net_in" else "out"
                    metrics["interfaces"][iface][sub]["history"].append([clock_ms, round(val, 2)])

            payload_probs = {
                "jsonrpc": "2.0", "method": "problem.get",
                "params": {
                    "output": ["name", "clock", "severity"],
                    **param_filter,
                    "sortfield": ["eventid"], "sortorder": "DESC", "limit": 10
                },
                "auth": self.auth_token, "id": 7
            }
            resp_probs = await client.post(self.url, json=payload_probs, timeout=10.0)
            metrics["recent_problems"] = resp_probs.json().get("result", [])

            return metrics

    async def get_global_trends(self, time_from: int = None, time_till: int = None):
        hosts = await self.get_all_hosts(time_from=time_from, time_till=time_till)
        if not hosts: return {"cpu_trends": [], "ram_trends": []}
        
        top_cpu = sorted(hosts, key=lambda x: x["cpu"], reverse=True)[:5]
        top_ram = sorted(hosts, key=lambda x: x["ram"], reverse=True)[:5]
        
        return {
            "cpu_trends": [{"name": h["hostname"], "data": h["cpu_history"]} for h in top_cpu],
            "ram_trends": [{"name": h["hostname"], "data": h["ram_history"]} for h in top_ram]
        }
