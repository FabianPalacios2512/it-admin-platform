import winrm
from app.core.config import get_primary_server

cfg = get_primary_server("da")
print(f"IP: {cfg['ip']}, User: {cfg['admin_user']}")

session = winrm.Session(cfg["ip"], auth=(cfg["admin_user"], cfg["admin_pass"]), transport='ntlm', server_cert_validation='ignore')

script = """
$ErrorActionPreference = 'Stop'
New-GPO -Name "Agente_Prueba_Automatica" | Out-Null
Set-GPRegistryValue -Name "Agente_Prueba_Automatica" -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" -ValueName "Wallpaper" -Type String -Value "\\\\192.168.20.110\\Fondos de pantalla\\Fondodepantalla.jpg"
Write-Output "GPO CREADA EXITOSAMENTE"
"""

print("Running script via WinRM...")
r = session.run_ps(script)

if r.std_out:
    print("STDOUT:", r.std_out.decode('cp850', errors='ignore'))
if r.std_err:
    print("STDERR:", r.std_err.decode('cp850', errors='ignore'))
print("Status Code:", r.status_code)
