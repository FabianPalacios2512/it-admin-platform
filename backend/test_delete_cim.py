import sys
sys.path.append('.')
from app.services.printer_service import _run_invoke_command

script = """
 = Get-CimInstance Win32_Printer -Filter "Name='moda y hogar'"
if () { Remove-CimInstance -InputObject  }
"""
try:
    print("Deleting moda y hogar via CIM...")
    out = _run_invoke_command(script)
    print("OUTPUT:", out)
except Exception as e:
    print("ERROR:", e)
