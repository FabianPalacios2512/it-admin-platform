import sys
import subprocess
from app.core.database import SessionLocal
from app.models.server import ServerConfig
from app.core.encryption import decrypt_password

db = SessionLocal()
server = db.query(ServerConfig).filter(ServerConfig.ip == '192.168.20.100').first()
ip = server.ip
admin_user = server.admin_user
admin_pass = decrypt_password(server.admin_pass)
domain = server.domain
if domain and '\\' not in admin_user and '@' not in admin_user:
    admin_user = f'{domain}\\{admin_user}'
safe_pass = admin_pass.replace("'", "''")

ps_script = """
$procs = Get-Process | Where-Object {$_.CPU -gt 0} | Sort-Object CPU -Descending | Select-Object -First 5
$result = $procs | ForEach-Object {
    $uptime = 1
    if ($_.StartTime) {
        $uptime = [math]::Max(1, ((Get-Date) - $_.StartTime).TotalSeconds)
    }
    $cpuPercent = [math]::Round($_.CPU / $uptime * 100, 1)
    $memMb = [math]::Round($_.WorkingSet64 / 1MB, 1)
    [PSCustomObject]@{
        pid = $_.Id
        name = $_.ProcessName
        cpu_percent = $cpuPercent
        mem_percent = $memMb
    }
}
$result | ConvertTo-Json -Compress
"""

wmi_script = f"""
$password = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential ('{admin_user}', $password)
Invoke-Command -ComputerName '{ip}' -Credential $cred -ScriptBlock {{
    {ps_script}
}}
"""

res = subprocess.run(
    ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', '-'],
    input=wmi_script, capture_output=True, text=True,
    encoding='utf-8', errors='replace', timeout=20
)
print('STDOUT:', res.stdout)
print('STDERR:', res.stderr)
db.close()
