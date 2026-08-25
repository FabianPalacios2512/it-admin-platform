"""
Test real: Revocar la reserva de la MAC 00:0c:29:9d:33:16 (RH-ML-55667)
"""
import requests
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FG_IP = "192.168.40.25"
FG_TOKEN = "0pxy6pw06H3qjQkxxdhQgNqGpHfNfm"
BASE_CMDB = f"https://{FG_IP}/api/v2/cmdb"
HEADERS = {
    "Authorization": f"Bearer {FG_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}
TARGET_MAC = "00:0c:29:9d:33:16"
SERVER_ID = 2

# 1. Ver reservas actuales
r = requests.get(f"{BASE_CMDB}/system.dhcp/server/{SERVER_ID}/reserved-address", headers=HEADERS, verify=False)
data = r.json()
print("Reservas actuales:")
reservations = data.get("results", [])
for res in reservations:
    print(f"  ID={res.get('id')} MAC={res.get('mac')} IP={res.get('ip')}")

# 2. Buscar el ID de la reserva de la MAC objetivo
target_id = None
for res in reservations:
    if res.get("mac", "").lower() == TARGET_MAC.lower():
        target_id = res.get("id")
        print(f"\nEncontrada reserva con ID={target_id} para {TARGET_MAC}")
        break

if not target_id:
    print(f"\nMAC {TARGET_MAC} NO tiene reserva activa. Nada que revocar.")
else:
    # 3. Hacer el DELETE
    url_delete = f"{BASE_CMDB}/system.dhcp/server/{SERVER_ID}/reserved-address/{target_id}"
    print(f"\nDELETE {url_delete}")
    r2 = requests.delete(url_delete, headers=HEADERS, verify=False, timeout=10)
    print(f"Status: {r2.status_code}")
    print(f"Response: {r2.text[:1000]}")
    if r2.status_code == 200:
        resp_json = r2.json()
        if resp_json.get("status") == "success":
            print("\nReserva REVOCADA correctamente!")
        else:
            print(f"\nError en respuesta: {resp_json}")
