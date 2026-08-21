"""
Prueba real de GPO via WMI+SMB (el mismo canal que ya usa AdInfra).
No imprime credenciales.
"""
import socket
import subprocess
import sys
import time
import uuid
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.config import get_primary_server

WALLPAPER = r"\\192.168.20.110\Fondos de pantalla\Fondodepantalla.jpg"
GPO_NAME = "Fondo_Pantalla_AdInfra"
RESULT_FILE = Path(__file__).with_name("gpo_wmi_result.txt")


def mask(text: str, *secrets: str) -> str:
    out = text or ""
    for s in secrets:
        if s:
            out = out.replace(s, "********")
    return out


def tcp_check(ip: str, port: int, timeout: float = 4.0) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        return "OPEN"
    except socket.timeout:
        return "TIMEOUT"
    except OSError as e:
        return f"CLOSED ({e.strerror})"
    finally:
        s.close()


def run(cmd, timeout=40):
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def main():
    lines = []
    def log(msg):
        print(msg)
        lines.append(msg)

    cfg = get_primary_server("da")
    ip = cfg["ip"]
    user = cfg["admin_user"]
    password = cfg["admin_pass"]
    safe_pass = password.replace("'", "''")

    log("=== 1) CONECTIVIDAD TCP AL DC ===")
    log(f"DC IP: {ip}")
    log(f"User: {user}")
    for port, name in [(445, "SMB"), (135, "RPC/WMI"), (389, "LDAP"), (5985, "WinRM HTTP")]:
        log(f"  puerto {port} ({name}): {tcp_check(ip, port)}")

    log("")
    log("=== 2) WALLPAPER UNC ===")
    wallpaper_ok = Path(WALLPAPER).exists()
    log(f"  {WALLPAPER}: {'EXISTE' if wallpaper_ok else 'NO ACCESIBLE'}")

    log("")
    log("=== 3) SMB IPC$ / C$ ===")
    ipc = f"\\\\{ip}\\IPC$"
    run(["net", "use", ipc, "/delete", "/y"])
    smb = run(["net", "use", ipc, password, f"/user:{user}"])
    log(f"  net use IPC$: rc={smb.returncode}")
    if smb.returncode != 0:
        log("  STDERR: " + mask((smb.stderr or smb.stdout or "").strip(), password))
        RESULT_FILE.write_text("\n".join(lines), encoding="utf-8")
        return 1

    log("")
    log("=== 4) WMI Win32_Process en el DC ===")
    guid = str(uuid.uuid4())
    remote_out = f"C:\\Windows\\Temp\\gpo_{guid}.txt"
    unc_out = f"\\\\{ip}\\C$\\Windows\\Temp\\gpo_{guid}.txt"

    ps_on_dc = f"""
$ErrorActionPreference = 'Stop'
$gpoName = '{GPO_NAME}'
$wallpaper = '{WALLPAPER}'
try {{
    Import-Module GroupPolicy -ErrorAction Stop
    $existing = Get-GPO -Name $gpoName -ErrorAction SilentlyContinue
    if (-not $existing) {{
        New-GPO -Name $gpoName | Out-Null
        'CREATED' | Out-File -FilePath '{remote_out}' -Encoding utf8
    }} else {{
        'EXISTS' | Out-File -FilePath '{remote_out}' -Encoding utf8
    }}
    Set-GPRegistryValue -Name $gpoName -Key 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -ValueName 'Wallpaper' -Type String -Value $wallpaper
    Set-GPRegistryValue -Name $gpoName -Key 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -ValueName 'WallpaperStyle' -Type String -Value '2'
    Add-Content -Path '{remote_out}' -Value 'WALLPAPER_SET'
    $gpo = Get-GPO -Name $gpoName
    Add-Content -Path '{remote_out}' -Value ('GUID=' + $gpo.Id)
    Add-Content -Path '{remote_out}' -Value 'OK'
}} catch {{
    'ERROR: ' + $_.Exception.Message | Out-File -FilePath '{remote_out}' -Encoding utf8
}}
"""
    encoded = base64.b64encode(ps_on_dc.encode("utf-16le")).decode("ascii")
    cmd = f"powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -EncodedCommand {encoded}"

    wmi_script = f"""
$password = ConvertTo-SecureString '{safe_pass}' -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential ('{user}', $password)
$res = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList '{cmd}' -ComputerName '{ip}' -Credential $cred
if ($null -eq $res) {{ throw 'WMI no devolvio resultado' }}
if ($res.ReturnValue -ne 0) {{ throw "WMI Error ReturnValue=$($res.ReturnValue)" }}
Write-Output "PID=$($res.ProcessId)"
"""
    wmi = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", wmi_script], timeout=60)
    log(f"  WMI rc={wmi.returncode}")
    log("  STDOUT: " + mask((wmi.stdout or "").strip(), password, safe_pass))
    if wmi.returncode != 0:
        log("  STDERR: " + mask((wmi.stderr or "").strip(), password, safe_pass))
        RESULT_FILE.write_text("\n".join(lines), encoding="utf-8")
        return 1

    log("")
    log("=== 5) ESPERANDO RESULTADO EN C$ ===")
    output = ""
    for i in range(25):
        time.sleep(1)
        check = run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"if (Test-Path '{unc_out}') {{ Get-Content '{unc_out}' -Raw }}",
            ]
        )
        if check.returncode == 0 and check.stdout.strip():
            output = check.stdout.strip()
            log(f"  archivo listo en {i+1}s")
            break
    if not output:
        log("  TIMEOUT: el DC no escribio el archivo de resultado.")
        log("  WMI arranco el proceso, pero GroupPolicy no respondio a tiempo.")
        RESULT_FILE.write_text("\n".join(lines), encoding="utf-8")
        return 1

    log("  RESULTADO REMOTO:")
    for line in output.splitlines():
        log("    " + line)

    run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"if (Test-Path '{unc_out}') {{ Remove-Item '{unc_out}' -Force }}",
        ]
    )

    ok = "OK" in output and "ERROR:" not in output
    log("")
    log("=== VEREDICTO ===")
    if ok:
        log(f"GPO '{GPO_NAME}' creado/actualizado en el DC con wallpaper:")
        log(f"  {WALLPAPER}")
        log("No se vinculo a ninguna OU (eso se hace desde la UI).")
    else:
        log("Fallo remoto al crear/configurar el GPO.")

    RESULT_FILE.write_text("\n".join(lines), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
