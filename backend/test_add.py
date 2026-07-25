import sys
sys.path.append('.')
from app.services.printer_service import _run_invoke_command

script = """
     = Get-PrinterPort -Name 'IP_192.168.12.14' -ErrorAction SilentlyContinue
    if (-not ) {
        Add-PrinterPort -Name 'IP_192.168.12.14' -PrinterHostAddress '192.168.12.14'
    }
    Add-Printer -Name 'PLAYATTT' -DriverName 'HP Universal Printing PCL 6' -PortName 'IP_192.168.12.14' -Shared:False 
"""
try:
    print("RUNNING...")
    _run_invoke_command(script)
    print("DONE.")
except Exception as e:
    print("ERROR:", e)
