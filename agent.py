import sys
import subprocess
import os
import json
import socket
import ssl
import base64
import hashlib
import struct
import argparse
import platform

def print_banner():
    banner = """
    ===================================================
      [ ZERO TRUST DIAGNOSTIC ENGINE - LINUX/MAC ]
      CORP GRADE REMOTE IT FORENSICS (STANDALONE)
    ===================================================
    """
    print(banner)

def get_machine_info(issue: str) -> dict:
    hostname = socket.gethostname()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"

    os_info = f"{platform.system()} {platform.release()}"

    return {
        "type": "machine_info",
        "hostname": hostname,
        "ip": ip,
        "os": os_info,
        "issue": issue
    }

def is_command_allowed(cmd: str) -> tuple[bool, str]:
    # Basic whitelist/blacklist for readonly commands
    blocked_patterns = [
        "rm -", "mv ", "cp ", "chmod ", "chown ", "wget ", "curl ",
        "reboot", "shutdown", "kill ", "pkill ", ">", "mkfs", "dd ",
        "apt-get ", "apt ", "yum ", "dnf ", "pacman ", "systemctl stop",
        "systemctl restart", "systemctl disable", "nano ", "vim ", "vi "
    ]
    
    cmd_lower = cmd.lower()
    for bp in blocked_patterns:
        if bp in cmd_lower:
            return False, f"Command contains blocked pattern: {bp}"
            
    return True, ""

def execute_command(cmd: str) -> dict:
    print(f"[+] Executing: {cmd}")
    allowed, msg = is_command_allowed(cmd)
    if not allowed:
        print(f"[-] Blocked: {msg}")
        return {
            "type": "command_blocked",
            "command": cmd,
            "message": msg
        }
    
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        try:
            stdout, stderr = proc.communicate(timeout=30.0)
            return {
                "type": "command_result",
                "command": cmd,
                "stdout": stdout.decode(errors='replace'),
                "stderr": stderr.decode(errors='replace'),
                "exit_code": proc.returncode
            }
        except subprocess.TimeoutExpired:
            proc.kill()
            return {
                "type": "command_result",
                "command": cmd,
                "stdout": "",
                "stderr": "Command timed out after 30 seconds",
                "exit_code": -1
            }
    except Exception as e:
        return {
            "type": "error",
            "message": f"Execution failed: {str(e)}"
        }

class SimpleWS:
    def __init__(self, url):
        self.url = url
        url = url.replace("wss://", "")
        if "/" in url:
            host_port, path = url.split("/", 1)
            path = "/" + path
        else:
            host_port = url
            path = "/"
            
        if ":" in host_port:
            host, port = host_port.split(":")
            port = int(port)
        else:
            host = host_port
            port = 443
            
        self.sock = socket.create_connection((host, port), timeout=10)
        context = ssl.create_default_context()
        self.sock = context.wrap_socket(self.sock, server_hostname=host)
        
        # Handshake
        key = base64.b64encode(os.urandom(16)).decode('utf-8')
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.sock.sendall(req.encode('utf-8'))
        resp = self.sock.recv(4096).decode('utf-8', errors='ignore')
        if "101 Switching Protocols" not in resp:
            raise Exception("Handshake failed:\n" + resp)
            
        self.sock.settimeout(None)
            
    def send(self, data: str):
        data_bytes = data.encode('utf-8')
        length = len(data_bytes)
        header = bytearray([0x81]) # FIN + TEXT
        if length <= 125:
            header.append(length | 0x80)
        elif length >= 126 and length <= 65535:
            header.append(126 | 0x80)
            header.extend(struct.pack(">H", length))
        else:
            header.append(127 | 0x80)
            header.extend(struct.pack(">Q", length))
            
        mask = os.urandom(4)
        header.extend(mask)
        masked_data = bytearray(length)
        for i in range(length):
            masked_data[i] = data_bytes[i] ^ mask[i % 4]
        self.sock.sendall(header + masked_data)
        
    def recv(self) -> str:
        header = self.sock.recv(2)
        if not header:
            raise Exception("Connection closed")
        b1, b2 = header[0], header[1]
        opcode = b1 & 0x0f
        masked = b2 & 0x80
        length = b2 & 0x7f
        
        if length == 126:
            length = struct.unpack(">H", self.sock.recv(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self.sock.recv(8))[0]
            
        if masked:
            mask = self.sock.recv(4)
            
        data = bytearray()
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk:
                raise Exception("Connection closed during recv")
            data.extend(chunk)
            
        if masked:
            for i in range(len(data)):
                data[i] ^= mask[i % 4]
                
        if opcode == 8:
            raise Exception("Connection closed by server")
        elif opcode == 9: # PING
            # Client MUST mask all frames sent to server (RFC 6455)
            # PONG payload must be identical to PING payload
            pong_header = bytearray([0x8A, length | 0x80])
            pong_mask = os.urandom(4)
            pong_header.extend(pong_mask)
            pong_data = bytearray(length)
            for i in range(length):
                pong_data[i] = data[i] ^ pong_mask[i % 4]
            self.sock.sendall(pong_header + pong_data)
            return self.recv()
        elif opcode == 10: # PONG
            return self.recv()
            
        return data.decode('utf-8', errors='replace')
        
    def close(self):
        try:
            self.sock.close()
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description="IT Diagnostic Agent")
    parser.add_argument("--server", required=True, help="Backend Server URL")
    parser.add_argument("--issue", required=True, help="Issue description")
    args = parser.parse_args()

    print_banner()

    ws_url = args.server.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url.rstrip('/')}/api/v1/diagnostics/ws"

    print(f"[*] Connecting to {ws_url}...")
    
    ws = None
    try:
        ws = SimpleWS(ws_url)
        print("[+] Connected to Diagnostic Engine.")
        
        machine_info = get_machine_info(args.issue)
        ws.send(json.dumps(machine_info))
        
        while True:
            try:
                message_str = ws.recv()
                if not message_str.strip():
                    continue
                data = json.loads(message_str)
                msg_type = data.get("type")
                
                if msg_type == "execute_command":
                    cmd = data.get("command", "")
                    result = execute_command(cmd)
                    ws.send(json.dumps(result))
                    
                elif msg_type == "status_update":
                    print(f"[*] Status: {data.get('message')}")
                    
                elif msg_type == "diagnosis_complete":
                    print("\\n" + "="*50)
                    print(" DIAGNOSIS COMPLETE")
                    print("="*50)
                    print(f"Message: {data.get('message')}")
                    report = data.get("report", {})
                    print(f"Severity: {report.get('severity')}")
                    print(f"Root Cause: {report.get('root_cause')}")
                    print("Recommendations:")
                    for r in report.get("recommendations", []):
                        print(f"  - {r}")
                    break
                    
                elif msg_type == "error":
                    print(f"[!] ERROR: {data.get('message')}")
                    if data.get("fatal"):
                        break
                        
                elif msg_type == "diagnosis_incomplete":
                    print(f"[!] INCOMPLETE: {data.get('message')}")
                    break
                    
            except Exception as e:
                if "Connection closed by server" in str(e):
                    print("[-] Connection closed by server.")
                else:
                    print(f"[-] Error processing message: {e}")
                break
                
    except Exception as e:
        print(f"[-] Failed to connect: {e}")
    finally:
        if ws:
            ws.close()

if __name__ == "__main__":
    main()
