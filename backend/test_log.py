import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('190.145.227.29', port=22, username='root', password='P0w2rb00k2021*')

stdin, stdout, stderr = client.exec_command('grep -rn "8005442033477471" /var/log/asterisk/ 2>/dev/null')
print(stdout.read().decode('utf-8'))
