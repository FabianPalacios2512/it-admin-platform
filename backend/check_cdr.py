import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('190.145.227.29', port=22, username='root', password='P0w2rb00k2021*')

stdin, stdout, stderr = client.exec_command('tail -n 20 /var/log/asterisk/cdr-csv/Master.csv 2>/dev/null')
print(stdout.read().decode('utf-8').strip())

if not stdout.read().decode('utf-8').strip():
    print("Trying /var/log/asterisk/full")
    stdin, stdout, stderr = client.exec_command("tail -n 100 /var/log/asterisk/full | grep 'Dial('")
    print(stdout.read().decode('utf-8').strip())
