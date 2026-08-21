"""Ejecuta PowerShell en el Domain Controller via WMI + SMB."""
import base64
import logging
import subprocess
import time
import uuid

from app.core.config import get_primary_server

logger = logging.getLogger(__name__)


def run_on_dc(script: str, *, wait_s: int = 35, capture: bool = False) -> str:
    cfg = get_primary_server("da")
    ip = cfg["ip"]
    admin_user = cfg["admin_user"]
    admin_pass = cfg["admin_pass"]
    safe_pass = admin_pass.replace("'", "''")

    guid = str(uuid.uuid4())
    remote_out = f"C:\\Windows\\Temp\\gpo_{guid}.txt"
    unc_out = f"\\\\{ip}\\C$\\Windows\\Temp\\gpo_{guid}.txt"

    if capture:
        wrapped = f"""
$ErrorActionPreference = 'Stop'
try {{
    Import-Module GroupPolicy -ErrorAction Stop
    $__result = & {{
{script}
    }}
    if ($null -eq $__result) {{ $text = '' }}
    elseif ($__result -is [string]) {{ $text = $__result }}
    else {{ $text = ($__result | Out-String).Trim() }}
    Set-Content -Path '{remote_out}' -Value $text -Encoding UTF8
}} catch {{
    Set-Content -Path '{remote_out}' -Value ('ERROR: ' + $_.Exception.Message) -Encoding UTF8
}}
"""
    else:
        wrapped = f"""
$ErrorActionPreference = 'Stop'
try {{
    Import-Module GroupPolicy -ErrorAction Stop
{script}
    'OK' | Out-File -FilePath '{remote_out}' -Encoding utf8
}} catch {{
    ('ERROR: ' + $_.Exception.Message) | Out-File -FilePath '{remote_out}' -Encoding utf8
}}
"""

    encoded = base64.b64encode(wrapped.encode("utf-16le")).decode("ascii")
    cmd = f"powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand {encoded}"
    wmi_script = f"""
$password = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential ('{admin_user}', $password)
$res = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList '{cmd}' -ComputerName '{ip}' -Credential $cred
if ($null -eq $res) {{ throw 'WMI no devolvio resultado' }}
if ($res.ReturnValue -ne 0) {{ throw "WMI Error ReturnValue=$($res.ReturnValue)" }}
Write-Output "PID=$($res.ProcessId)"
"""

    ipc = f"\\\\{ip}\\IPC$"
    subprocess.run(["net", "use", ipc, "/delete", "/y"], capture_output=True)
    smb = subprocess.run(
        ["net", "use", ipc, admin_pass, f"/user:{admin_user}"],
        capture_output=True,
        text=True,
    )
    if smb.returncode != 0:
        err = (smb.stderr or smb.stdout or "").replace(admin_pass, "********")
        raise Exception(f"No se pudo abrir SMB hacia el DC {ip}: {err}")

    wmi = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", wmi_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if wmi.returncode != 0:
        err = (wmi.stderr or wmi.stdout or "").replace(admin_pass, "********").replace(safe_pass, "********")
        raise Exception(f"WMI fallo en el DC {ip}: {err}")

    output = ""
    for _ in range(wait_s):
        time.sleep(1)
        check = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"if (Test-Path '{unc_out}') {{ Get-Content '{unc_out}' -Raw }}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if check.returncode == 0 and check.stdout.strip():
            output = check.stdout.strip()
            break

    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         f"if (Test-Path '{unc_out}') {{ Remove-Item '{unc_out}' -Force }}"],
        capture_output=True,
    )

    if not output:
        raise Exception("Timeout esperando el resultado del DC.")
    if output.startswith("ERROR:"):
        raise Exception(output)
    return output
