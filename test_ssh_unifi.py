import paramiko
import time

def unifi_set_inform(ip, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f'Intentando conectar a {ip} con {username}...')
    try:
        client.connect(ip, username=username, password=password, timeout=5)
        print('Conexion exitosa!')
        
        stdin, stdout, stderr = client.exec_command('info')
        print('INFO del AP:', stdout.read().decode())
        
        print('Enviando set-inform...')
        stdin, stdout, stderr = client.exec_command('set-inform http://192.168.1.111:8080/inform')
        print(stdout.read().decode())
        
        client.close()
        return True
    except Exception as e:
        print(f'Fallo con la password: {e}')
        return False

ap_ip = '172.16.30.13' # DataCenter AP
if not unifi_set_inform(ap_ip, 'ubnt', 'N1b3lung0s.1.2.3*'):
    print('Probando con password default ubnt...')
    unifi_set_inform(ap_ip, 'ubnt', 'ubnt')
