import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IP = "192.168.40.25"
TOKEN = "0pxy6pw06H3qjQkxxdhQgNqGpHfNfm"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

print("=== DHCP ===")
dhcp = requests.get(f"https://{IP}/api/v2/monitor/system/dhcp", headers=HEADERS, verify=False).json()
print(dhcp.get('results', dhcp)[:2])

print("\n=== ROUTING ===")
routes = requests.get(f"https://{IP}/api/v2/monitor/router/ipv4", headers=HEADERS, verify=False).json()
print(routes.get('results', routes)[:2])

print("\n=== SESSIONS ===")
sessions = requests.get(f"https://{IP}/api/v2/monitor/firewall/session", headers=HEADERS, verify=False).json()
res = sessions.get('results', sessions)
if isinstance(res, list):
    print(res[:2])
else:
    print(res)
