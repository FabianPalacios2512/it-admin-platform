from agent import SimpleWS
import json

ws = SimpleWS('wss://echo.websocket.events/')
ws.recv() # read welcome message

payload = "x" * 500
ws.send(payload)
print("Sent")

resp = ws.recv()
print("Received length:", len(resp))
if resp == payload:
    print("SUCCESS")
else:
    print("FAILED")
