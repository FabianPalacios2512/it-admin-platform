import sys
sys.path.append('.')
from app.services.printer_service import _run_invoke_command

script = """
Add-PrinterPort -Name 'IP_TEST_SNMP7' -PrinterHostAddress '192.168.9.9'
Get-CimInstance -ClassName Win32_TCPIPPrinterPort -Filter "Name='IP_TEST_SNMP7'" | Set-CimInstance -Property @{SNMPEnabled=False}
 = Get-PrinterPort -Name 'IP_TEST_SNMP7'
Write-Output .SNMPEnabled
"""
try:
    out = _run_invoke_command(script)
    print("OUTPUT:", out)
except Exception as e:
    print("ERROR:", e)

# cleanup
_run_invoke_command("Remove-PrinterPort -Name 'IP_TEST_SNMP7'")
