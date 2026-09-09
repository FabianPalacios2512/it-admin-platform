import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('190.145.227.29', port=22, username='root', password='P0w2rb00k2021*')

print('--- Top IPs that attacked on Sep 6 ---')
stdin, stdout, stderr = client.exec_command("grep 'Sep  6' /var/log/secure | grep 'Failed password' | awk '{print $11}' | sort | uniq -c | sort -nr | head -5")
print(stdout.read().decode('utf-8'))

print('--- Checking Fail2Ban Status ---')
stdin, stdout, stderr = client.exec_command("fail2ban-client status sshd")
print(stdout.read().decode('utf-8'))

print('--- Checking Iptables ---')
stdin, stdout, stderr = client.exec_command("iptables -nL | grep DROP | head -5")
print(stdout.read().decode('utf-8'))
