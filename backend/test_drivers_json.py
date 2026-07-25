import sys
sys.path.append('.')
from app.services.printer_service import _run_invoke_command
import json

script = """
 = Get-PrinterDriver | Select-Object -ExpandProperty Name

"""
try:
    output = _run_invoke_command(script, return_json=True)
    data = json.loads(output)
    print("DATA TYPE:", type(data))
    if isinstance(data, list) and len(data) > 0:
        print("FIRST ITEM TYPE:", type(data[0]))
        print("FIRST ITEM:", data[0])
except Exception as e:
    print(e)
