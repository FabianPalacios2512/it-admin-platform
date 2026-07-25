import sys
sys.path.append('.')
from app.services.printer_service import _run_invoke_command

script = """
Set-WmiInstance -Class Win32_TCPIPPrinterPort -Arguments @{ Name="IP_TEST_WMI_3"; HostAddress="192.168.9.9"; PortNumber=9100; Protocol=1; SNMPEnabled=0 }
"""
try:
    out = _run_invoke_command(script)
    print("OUTPUT:", out)
except Exception as e:
    print("ERROR:", e)

# cleanup
_run_invoke_command("Remove-PrinterPort -Name 'IP_TEST_WMI_3' -ErrorAction SilentlyContinue")
