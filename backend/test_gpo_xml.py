from app.services.dc_exec import run_on_dc

script = """
$gpo = Get-GPO -Name "GPO_Inventario_Equipos"
Get-GPOReport -Guid $gpo.Id -ReportType Xml
"""
xml = run_on_dc(script, capture=True)
print(xml)
