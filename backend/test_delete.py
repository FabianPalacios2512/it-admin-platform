import sys
sys.path.append('.')
from app.services.printer_service import _run_invoke_command

try:
    print("Deleting moda y hogar...")
    out = _run_invoke_command("Remove-Printer -Name 'moda y hogar'")
    print("OUTPUT:", out)
except Exception as e:
    print("ERROR:", e)
