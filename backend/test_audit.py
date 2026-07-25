import sys
sys.path.append('.')
from app.services.printer_service import get_primary_server
import subprocess

cfg = get_primary_server("printers")
ip = cfg["ip"]
admin_user = cfg["admin_user"]
admin_pass = cfg["admin_pass"]
domain = cfg.get("domain", "")

if domain and "\\" not in admin_user and "@" not in admin_user:
    admin_user = f"{domain}\\{admin_user}"

safe_pass = admin_pass.replace("'", "''")

ps_script = f'''
Continue = "Stop"
 = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
 = New-Object System.Management.Automation.PSCredential ('{admin_user}', )

Invoke-Command -ComputerName '{ip}' -Credential  -ScriptBlock {{
     = Get-WinEvent -FilterHashtable @{{LogName="Microsoft-Windows-PrintService/Operational"; Id=307}} -MaxEvents 5 -ErrorAction SilentlyContinue
    if (-not ) {{
        Write-Output "[]"
        return
    }}
     = @()
    foreach ( in ) {{
         += [PSCustomObject]@{{
            Time = .TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')
            User = .Properties[2].Value
            Document = .Properties[1].Value
            Pages = .Properties[6].Value
        }}
    }}
     | ConvertTo-Json -Compress
}}
'''

res = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
