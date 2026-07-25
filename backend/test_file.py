import sys
sys.path.append('.')
import os
import subprocess

script = """
 = 'moda y hogar'
Write-Output "Printer: "
"""
with open("temp_exec.ps1", "w", encoding="utf-8-sig") as f:
    f.write(script)

res = subprocess.run(
    [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", "temp_exec.ps1"],
    capture_output=True, text=True
)
print("OUTPUT:", res.stdout)
print("ERROR:", res.stderr)
os.remove("temp_exec.ps1")
