import sys
sys.path.append('.')
from app.services.printer_service import _run_invoke_command

script = """
 = Get-PrinterDriver | Select-Object -ExpandProperty Name

"""
out = _run_invoke_command(script, return_json=True)
print(out)
