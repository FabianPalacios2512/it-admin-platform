from app.services.gpo_inspect import diagnose_gpo
import json

res = diagnose_gpo("GPO_Inventario_Equipos", with_settings=True)
print(json.dumps(res, indent=2))
