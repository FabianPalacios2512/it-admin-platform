import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print('Connecting to 192.168.40.25...')
    client.connect('192.168.40.25', username='admin', password='Medellin123456]]', timeout=10)
    shell = client.invoke_shell()
    time.sleep(1)
    shell.recv(9999)
    
    shell.send("config system api-user\nedit adminda2\nset accprofile super_admin\nset cors-allow-origin *\nnext\n")
    time.sleep(2)
    out = shell.recv(9999).decode('utf-8', errors='ignore')
    print("--- FIRST OUT ---")
    print(out)
    
    if "password" in out.lower():
        shell.send("Medellin123456]]\n")
        time.sleep(2)
        out += shell.recv(9999).decode('utf-8', errors='ignore')
    
    shell.send("end\n")
    time.sleep(1)
    
    shell.send("execute api-user generate-key adminda2\n")
    time.sleep(2)
    out += shell.recv(9999).decode('utf-8', errors='ignore')
    if "password" in out.lower():
        shell.send("Medellin123456]]\n")
        time.sleep(2)
        out += shell.recv(9999).decode('utf-8', errors='ignore')

    print("--- FINAL OUT ---")
    print(out)
    client.close()
except Exception as e:
    print('Error:', e)
