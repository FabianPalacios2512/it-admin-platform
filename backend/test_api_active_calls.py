import requests
import json
import os

token_file = r"c:\Users\fapaternina\OneDrive - Hogar y Moda S.A.S\Documentos\it-admin-platform-main\it-admin-platform-main\backend\test_token.txt"
try:
    with open(token_file, "r") as f:
        token = f.read().strip()
    
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get("http://127.0.0.1:8000/api/v1/zabbix/pbx/active-calls", headers=headers, timeout=15)
    print("Status code:", res.status_code)
    try:
        data = res.json()
        print("Calls returned:", data.get("total", 0))
    except Exception as e:
        print("Response text:", res.text)
except Exception as e:
    print("Error:", e)
