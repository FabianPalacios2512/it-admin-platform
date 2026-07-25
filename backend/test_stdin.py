import sys
sys.path.append('.')

script = """& {
 = 'moda y hogar'
Write-Output "PRINTER IS: "
}"""

import subprocess
res = subprocess.run(
    [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "-"],
    input=script,
    capture_output=True, text=True
)
print("OUTPUT:", res.stdout)
print("ERROR:", res.stderr)
