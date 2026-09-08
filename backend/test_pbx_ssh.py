import paramiko

PBX_HOST = "190.145.227.29"
PBX_USER = "root"
PBX_PASS = "P0w2rb00k2021*"
PBX_PORT = 22

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(PBX_HOST, port=PBX_PORT, username=PBX_USER, password=PBX_PASS, timeout=10)
    stdin, stdout, stderr = ssh.exec_command("asterisk -rx 'core show channels concise'", timeout=10)
    raw = stdout.read().decode("utf-8", errors="ignore")
    print("STDOUT:", raw)
    err = stderr.read().decode("utf-8", errors="ignore")
    print("STDERR:", err)
    ssh.close()
except Exception as e:
    print("ERROR:", str(e))
