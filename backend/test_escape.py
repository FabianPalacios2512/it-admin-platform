import sys
sys.path.append('.')

script = """
 = 'moda y hogar'
Write-Output 
"""
# Escape $ for powershell command line:
escaped_script = script.replace('$', '$')

import subprocess
res = subprocess.run(
    [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile", "-NonInteractive", "-Command", escaped_script],
    capture_output=True, text=True
)
print("OUTPUT:", res.stdout)
print("ERROR:", res.stderr)
