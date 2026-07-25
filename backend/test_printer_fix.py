import sys
sys.path.append('.')
from app.services.printer_service import get_primary_server
import subprocess
import win32print
import win32security

try:
    cfg = get_primary_server("printers")
    ip = cfg["ip"]
    admin_user = cfg["admin_user"]
    admin_pass = cfg["admin_pass"]
    domain = cfg.get("domain", "")
    if domain and "\\" not in admin_user:
        admin_user = f"{domain}\\{admin_user}"
        
    subprocess.run(["net", "use", f"\\\\{ip}\\IPC$", "/delete", "/y"], capture_output=True)
    subprocess.run(["net", "use", f"\\\\{ip}\\IPC$", admin_pass, f"/user:{admin_user}"], capture_output=True)
    
    # Try native win32print EnumJobs
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_NAME, f"\\\\{ip}", 2)
    if printers:
        name = printers[0].get('pPrinterName', '')
        if '\\' in name:
            name = name.split('\\')[-1]
        print(f"Test Printer: {name}")
        
        # Test PrintTestPage via local PS CIM
        ps_script = f'''
         = ConvertTo-SecureString '{admin_pass}' -AsPlainText -Force
         = New-Object System.Management.Automation.PSCredential ('{admin_user}', )
         = New-CimSession -ComputerName '{ip}' -Credential 
         = Get-CimInstance Win32_Printer -CimSession  -Filter "Name='{name}'"
        if () {{
            Write-Host "Found printer via CIM"
        }} else {{
            Write-Host "Printer not found via CIM"
        }}
        Remove-CimSession 
        '''
        res = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
        print("CIM Test:", res.stdout)
        if res.stderr:
            print("CIM Error:", res.stderr)
except Exception as e:
    print(f"Error: {e}")
