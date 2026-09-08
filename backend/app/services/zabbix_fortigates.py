import httpx
import logging
import asyncio
from typing import List, Dict

logger = logging.getLogger(__name__)

async def get_zabbix_fortigates(url: str, username: str, password: str, target_hostid: str = None) -> Dict:
    async with httpx.AsyncClient(verify=False) as client:
        # 1. Login
        login_payload = {
            "jsonrpc": "2.0", "method": "user.login",
            "params": {"username": username, "password": password}, "id": 1
        }
        resp = await client.post(url, json=login_payload, timeout=10.0)
        auth = resp.json().get("result")
        if not auth:
            raise Exception("Failed to authenticate to Zabbix API")

        # 2. Get Hosts
        hosts_params = {
            "output": ["hostid", "name", "host", "available", "snmp_available", "status"],
            "selectInterfaces": ["ip"],
            "search": {"name": ["Forti", "FGT"]},
            "searchByAny": True
        }
        if target_hostid:
            hosts_params["hostids"] = [target_hostid]
            
        hosts_payload = {
            "jsonrpc": "2.0", "method": "host.get",
            "params": hosts_params,
            "auth": auth, "id": 2
        }
        resp = await client.post(url, json=hosts_payload, timeout=15.0)
        hosts = resp.json().get("result", [])
        if not hosts:
            return []
        
        host_ids = [h["hostid"] for h in hosts]

        # 3. Get Items and Triggers Concurrently
        search_keys = [
            "system.cpu.util", "vm.memory.util", "vm.memory.size", "fgSysCpu", "fgSysMem", 
            "session", "sescount", "vpn", "ipsec", "net.if.in", "net.if.out", "system.uptime", 
            "fgsyssesscount", "fgSysSesCount", "fgvpntunupcount", "fgipsintrusionsblocked",
            "icmppingsec", "icmppingloss", "ping", "sdwan_health.latency", "sdwan_health.loss"
        ]
        
        items_payload = {
            "jsonrpc": "2.0", "method": "item.get",
            "params": {
                "output": ["itemid", "hostid", "name", "key_", "lastvalue", "value_type"],
                "hostids": host_ids,
                "search": {"key_": search_keys},
                "searchByAny": True
            },
            "auth": auth, "id": 3
        }
        
        triggers_payload = {
            "jsonrpc": "2.0", "method": "trigger.get",
            "params": {
                "output": ["triggerid", "priority"],
                "selectHosts": ["hostid"],
                "hostids": host_ids,
                "filter": {"value": 1, "status": 0},
                "monitored": True
            },
            "auth": auth, "id": 4
        }
        
        items_resp, triggers_resp = await asyncio.gather(
            client.post(url, json=items_payload, timeout=60.0),
            client.post(url, json=triggers_payload, timeout=30.0)
        )
        
        items = items_resp.json().get("result", [])
        triggers = triggers_resp.json().get("result", [])

        # Process Triggers
        triggers_by_host = {hid: 0 for hid in host_ids}
        critical_by_host = {hid: False for hid in host_ids}
        for t in triggers:
            for th in t.get("hosts", []):
                hid = th["hostid"]
                triggers_by_host[hid] += 1
                if int(t.get("priority", 0)) >= 4:
                    critical_by_host[hid] = True

        # Process Data
        final_data = []
        history_itemids = []
        history_itemids_float = []
        for h in hosts:
            hid = h["hostid"]
            host_items = [i for i in items if i["hostid"] == hid]
            
            cpu = 0
            ram = 0
            sessions = 0
            vpn_up = 0
            vpn_down = 0
            uptime = 0
            ips_blocked = 0
            ping_ms = 0
            packet_loss = 0
            interfaces = {}
            
            mem_used = None
            mem_total = None
            has_ram_pct = False
            
            # Ordenamos los items por key_ para procesar net.if (tráfico) ANTES que sdwan_health (latencia)
            # Esto asegura que la interfaz real ya exista antes de intentar fusionar la métrica SD-WAN.
            host_items.sort(key=lambda x: x["key_"].lower())
            
            for item in host_items:
                key = item["key_"].lower()
                name = (item.get("name") or "").lower()
                raw_val = item.get("lastvalue")
                
                try:
                    val = float(raw_val) if raw_val else 0.0
                except (ValueError, TypeError):
                    continue
                    
                is_pct = 0 <= val <= 100
                looks_bytes = val > 1000 or (any(x in key for x in ["used", "free", "total", "size", "available", "capacity"]) and not any(x in key for x in ["util", "pused", "usage", "percent"]))
                
                if is_pct and ("cpu.util" in key or "cpu.usage" in key or "fgsyscpuusage" in key or "cpu util" in name):
                    cpu = round(val, 1)
                elif is_pct and not looks_bytes and ("memory.util" in key or "mem.util" in key or "memory.pused" in key or "mem.pused" in key or "fgsysmemusage" in key or "memory util" in name or "memory usage" in name or "used memory" in name):
                    ram = round(val, 1)
                    has_ram_pct = True
                elif "memory.size[used]" in key or "vm.memory.size[used]" in key or "fgsysmemused" in key:
                    mem_used = val
                elif "memory.size[total]" in key or "vm.memory.size[total]" in key or "fgsysmemcapacity" in key:
                    mem_total = val
                elif "system.uptime" in key:
                    uptime = int(val)
                elif ("sescount" in key or "sesscount" in key or "session" in key or "fgsysses" in key) or ("session" in name):
                    if not any(x in key for x in ["vpn", "ipsec", "timeout", "expire"]):
                        sessions = int(val)
                elif "fgipsintrusionsblocked" in key:
                    ips_blocked = int(val)
                elif "fgvpntunupcount" in key:
                    vpn_up = int(val)
                elif "vpn" in key or "ipsec" in key:
                    if "fgvpntunupcount" not in key:
                        if "status" in key:
                            if val == 1:
                                vpn_up += 1
                            else:
                                vpn_down += 1
                        else:
                            vpn_up += int(val)
                elif "net.if.in" in key and "discards" not in key and "errors" not in key:
                    import re
                    match = re.search(r"Interface (.*?):", item.get("name", ""))
                    if match:
                        ifname = match.group(1)
                        if ifname not in interfaces:
                            interfaces[ifname] = {"in_bps": 0, "out_bps": 0, "in_itemid": "", "out_itemid": "", "sdwan_latency": None, "sdwan_loss": None}
                        interfaces[ifname]["in_bps"] += val
                        interfaces[ifname]["in_itemid"] = item["itemid"]
                elif "net.if.out" in key and "discards" not in key and "errors" not in key:
                    import re
                    match = re.search(r"Interface (.*?):", item.get("name", ""))
                    if match:
                        ifname = match.group(1)
                        if ifname not in interfaces:
                            interfaces[ifname] = {"in_bps": 0, "out_bps": 0, "in_itemid": "", "out_itemid": "", "sdwan_latency": None, "sdwan_loss": None}
                        interfaces[ifname]["out_bps"] += val
                        interfaces[ifname]["out_itemid"] = item["itemid"]
                elif "sdwan_health.latency" in key or "sdwan_health.loss" in key:
                    import re
                    match = re.search(r"SD-WAN \[[^\]]+\]:\[([^\]]+)\]:", item.get("name", ""))
                    if match:
                        ifname = match.group(1)
                        # Match with existing real interfaces like "lan3(TIGO)" or "a(INTERCAM)"
                        real_ifname = ifname
                        for existing in interfaces.keys():
                            if existing == ifname or existing.startswith(ifname + "(") or existing.startswith(ifname + " "):
                                real_ifname = existing
                                break
                        if real_ifname not in interfaces:
                            interfaces[real_ifname] = {"in_bps": 0, "out_bps": 0, "in_itemid": "", "out_itemid": "", "sdwan_latency": None, "sdwan_loss": None, "sdwan_latency_itemid": None}
                        if "latency" in key:
                            interfaces[real_ifname]["sdwan_latency"] = val
                            interfaces[real_ifname]["sdwan_latency_itemid"] = item["itemid"]
                        elif "loss" in key:
                            interfaces[real_ifname]["sdwan_loss"] = val
                elif "icmppingsec" in key or "ping" in key:
                    ping_ms = round(val * 1000, 1) # seconds to ms
                elif "icmppingloss" in key or "pingloss" in key:
                    packet_loss = round(val, 1)

            if not has_ram_pct and mem_used and mem_total and mem_total > 0:
                ram = round((100.0 * mem_used) / mem_total, 1)
                if ram > 100: ram = 100

            has_critical = critical_by_host[hid]
            is_offline = (h.get("available") == "2" or h.get("snmp_available") == "2" or has_critical)
            status_text = "Offline" if is_offline else "Online"
            
            if is_offline:
                cpu = 0; ram = 0; sessions = 0; vpn_up = 0; vpn_down = 0; uptime = 0; ips_blocked = 0
                interfaces = {}

            uptime_str = "N/A"
            if uptime > 0:
                days = uptime // 86400
                hours = (uptime % 86400) // 3600
                minutes = (uptime % 3600) // 60
                if days > 0:
                    uptime_str = f"Up {days}d {hours}h"
                else:
                    uptime_str = f"Up {hours}h {minutes}m"

            active_interfaces = []
            for k, v in interfaces.items():
                if v["in_bps"] > 0 or v["out_bps"] > 0 or v.get("sdwan_latency") is not None:
                    active_interfaces.append({
                        "name": k,
                        "in_bps": v["in_bps"],
                        "out_bps": v["out_bps"],
                        "in_itemid": v["in_itemid"],
                        "out_itemid": v["out_itemid"],
                        "sdwan_latency": v.get("sdwan_latency"),
                        "sdwan_loss": v.get("sdwan_loss"),
                        "sdwan_latency_itemid": v.get("sdwan_latency_itemid"),
                        "sdwan_history": []
                    })
                    if v["in_itemid"]: history_itemids.append(v["in_itemid"])
                    if v["out_itemid"]: history_itemids.append(v["out_itemid"])
                    if v.get("sdwan_latency_itemid"): history_itemids_float.append(v["sdwan_latency_itemid"])

            final_data.append({
                "hostid": hid,
                "hostname": h.get("name", "Unknown"),
                "ip": h.get("interfaces", [{"ip": "N/A"}])[0].get("ip", "N/A") if h.get("interfaces") else "N/A",
                "status": status_text,
                "metrics": {
                    "cpu": cpu,
                    "ram": ram,
                    "active_sessions": sessions,
                    "uptime_str": uptime_str,
                    "ips_blocked": ips_blocked,
                    "vpn_tunnels_up": vpn_up,
                    "vpn": {"up": vpn_up, "down": vpn_down},
                    "interfaces": active_interfaces,
                    "alerts": triggers_by_host[hid],
                    "ping_ms": ping_ms,
                    "packet_loss": packet_loss
                }
            })
            
        # Optional: Fetch history for charts (last 30 mins) only if we request a specific host (side panel)
        if history_itemids and target_hostid:
            import time
            time_from = int(time.time() - (30 * 60)) # 30 mins
            history_payload = {
                "jsonrpc": "2.0", "method": "history.get",
                "params": {
                    "output": ["itemid", "clock", "value"],
                    "history": 3,
                    "itemids": history_itemids,
                    "time_from": time_from,
                    "sortfield": "clock",
                    "sortorder": "ASC"
                },
                "auth": auth, "id": 5
            }
            history_float_payload = {
                "jsonrpc": "2.0", "method": "history.get",
                "params": {
                    "output": ["itemid", "clock", "value"],
                    "history": 0,
                    "itemids": history_itemids_float,
                    "time_from": time_from,
                    "sortfield": "clock",
                    "sortorder": "ASC"
                },
                "auth": auth, "id": 6
            } if history_itemids_float else None
            
            try:
                # Concurrent requests to save time
                tasks = [client.post(url, json=history_payload, timeout=20.0)]
                if history_float_payload: tasks.append(client.post(url, json=history_float_payload, timeout=20.0))
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                h_data = responses[0].json().get("result", []) if not isinstance(responses[0], Exception) else []
                h_float_data = responses[1].json().get("result", []) if len(responses) > 1 and not isinstance(responses[1], Exception) else []
                
                history_lookup = {}
                history_float_lookup = {}
                for row in h_data:
                    iid = row["itemid"]
                    if iid not in history_lookup: history_lookup[iid] = []
                    history_lookup[iid].append({"clock": int(row["clock"]), "value": float(row["value"])})
                for row in h_float_data:
                    iid = row["itemid"]
                    if iid not in history_float_lookup: history_float_lookup[iid] = []
                    history_float_lookup[iid].append({"clock": int(row["clock"]), "value": float(row["value"])})
                    
                # Bind history
                from datetime import datetime
                for h in final_data:
                    for iface in h["metrics"]["interfaces"]:
                        in_hist = history_lookup.get(iface["in_itemid"], [])
                        out_hist = history_lookup.get(iface["out_itemid"], [])
                        
                        # Align by clock properly to avoid disjointed X/Y axes
                        merged_history = {}
                        for row in in_hist:
                            merged_history[row["clock"]] = {"in": row["value"], "out": 0}
                        for row in out_hist:
                            c = row["clock"]
                            if c not in merged_history:
                                merged_history[c] = {"in": 0, "out": row["value"]}
                            else:
                                merged_history[c]["out"] = row["value"]
                                
                        sorted_clocks = sorted(merged_history.keys())
                        
                        iface_history = []
                        for clock in sorted_clocks:
                            in_val = merged_history[clock]["in"] / 1000.0
                            out_val = merged_history[clock]["out"] / 1000.0
                            
                            dt = datetime.fromtimestamp(clock)
                            time_str = dt.strftime("%H:%M")
                            iface_history.append({
                                "time": time_str,
                                "clock": clock,
                                "in": round(in_val, 1),
                                "out": round(out_val, 1)
                            })
                        iface["history"] = iface_history
                        
                        # Parse SD-WAN History
                        if iface.get("sdwan_latency_itemid"):
                            sdwan_hist = history_float_lookup.get(iface["sdwan_latency_itemid"], [])
                            sdwan_arr = []
                            for row in sdwan_hist:
                                dt = datetime.fromtimestamp(row["clock"])
                                time_str = dt.strftime("%H:%M")
                                sdwan_arr.append({
                                    "time": time_str,
                                    "clock": row["clock"],
                                    "latency": round(row["value"], 1)
                                })
                            iface["sdwan_history"] = sdwan_arr
                            
            except Exception as e:
                logger.error(f"Failed to fetch history for fortigates: {e}")
                
        return final_data
