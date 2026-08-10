from agent import SimpleWS
import json

ws = SimpleWS('ws://localhost:8765')
ws.send(json.dumps({"type": "machine_info"}))
print('Sent machine_info')

msg = ws.recv()
print('Received:', msg)

# Create a 2000 byte string to force length >= 126
result = {"type": "command_result", "stdout": "x" * 2000, "stderr": "", "exit_code": 0}
ws.send(json.dumps(result))
print('Sent result')
