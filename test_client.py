from agent import SimpleWS
import json
import time

ws = SimpleWS('ws://127.0.0.1:8765/ws')
ws.send(json.dumps({"type": "machine_info"}))
print("Sent info")
msg = ws.recv()
print("Received msg")

# Try to send a 500 byte payload
payload = {"type": "command_result", "stdout": "x" * 500}
ws.send(json.dumps(payload))
print("Sent large payload")
