import sys
sys.path.append('.')
from app.services.printer_service import _run_invoke_command
import json

script = """
Get-PrinterDriver | Select-Object -ExpandProperty Name
"""
try:
    output = _run_invoke_command(script, return_json=True)
    print("OUTPUT:", output)
except Exception as e:
    print("ERROR:", e)
