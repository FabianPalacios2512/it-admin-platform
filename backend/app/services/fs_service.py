import wmi
import pythoncom
import os
import stat
import subprocess
import time
from datetime import datetime
from app.core.config import get_primary_server

# ══════════════════════════════════════════════════════════════
# CACHÉ DE CONEXIONES
# Evita re-crear la conexión WMI y SMB en cada petición.
# ══════════════════════════════════════════════════════════════

_wmi_cache = {"conn": None, "ip": None, "ts": 0}
_smb_cache = {"ip": None, "ts": 0}
_shares_cache = {"data": None, "ts": 0}

CACHE_TTL_WMI = 120       # 2 minutos
CACHE_TTL_SMB = 300        # 5 minutos
CACHE_TTL_SHARES = 30      # 30 segundos


def _get_wmi_connection():
    """Abre (o reutiliza) una conexión WMI con el servidor de archivos."""
    now = time.time()
    cfg = get_primary_server("files")
    ip = cfg["ip"]

    # Reutilizar si la caché es válida
    if (_wmi_cache["conn"] is not None
            and _wmi_cache["ip"] == ip
            and now - _wmi_cache["ts"] < CACHE_TTL_WMI):
        try:
            # Verificar que la conexión sigue viva con una consulta ligera
            _wmi_cache["conn"].Win32_OperatingSystem()
            return _wmi_cache["conn"]
        except Exception:
            _wmi_cache["conn"] = None  # Expiró, reconectar

    pythoncom.CoInitialize()
    try:
        conn = wmi.WMI(computer=ip, user=cfg["admin_user"], password=cfg["admin_pass"])
    except Exception as e:
        if "local connections" in str(e):
            conn = wmi.WMI()
        else:
            raise
    _wmi_cache["conn"] = conn
    _wmi_cache["ip"] = ip
    _wmi_cache["ts"] = now
    return conn


def authenticate_smb():
    """Autentica la sesión SMB. Reutiliza si ya hay una sesión reciente."""
    now = time.time()
    cfg = get_primary_server("files")
    ip = cfg["ip"]

    # Si ya tenemos sesión reciente, no reconectar
    if _smb_cache["ip"] == ip and now - _smb_cache["ts"] < CACHE_TTL_SMB:
        return ip

    user = cfg['admin_user'] if '\\' in cfg['admin_user'] else f"{cfg['domain']}\\{cfg['admin_user']}"
    password = cfg["admin_pass"]
    target = f"\\\\{ip}\\IPC$"

    # Intentar limpiar conexiones previas silenciosamente
    subprocess.run(["net", "use", target, "/delete"], capture_output=True)

    # Crear nueva conexión
    res = subprocess.run(["net", "use", target, password, f"/user:{user}"], capture_output=True, text=True)
    if res.returncode != 0:
        error_msg = res.stderr.replace(password, "********")
        raise ValueError(f"No se pudo autenticar SMB con el servidor. Error: {error_msg}")

    _smb_cache["ip"] = ip
    _smb_cache["ts"] = now
    return ip


# ══════════════════════════════════════════════════════════════
# CARPETAS COMPARTIDAS
# ══════════════════════════════════════════════════════════════

def get_shared_folders():
    """Obtiene la lista de carpetas compartidas (con caché de 30s)."""
    now = time.time()

    if _shares_cache["data"] is not None and now - _shares_cache["ts"] < CACHE_TTL_SHARES:
        return _shares_cache["data"]

    try:
        c = _get_wmi_connection()
        shares = c.Win32_Share(Type=0)

        cfg = get_primary_server("files")
        ip = cfg["ip"]

        results = []
        for share in shares:
            # Filtrar solo shares ocultos estándar del sistema, no los creados a medida
            if share.Name.upper() in ["ADMIN$", "IPC$", "C$", "D$", "E$", "F$", "PRINT$", "FAX$"]:
                continue

            results.append({
                "name": share.Name,
                "path": share.Path,
                "unc_path": f"\\\\{ip}\\{share.Name}",
                "description": share.Description if share.Description else "",
                "status": share.Status if hasattr(share, "Status") else "OK"
            })

        results.sort(key=lambda x: x['name'].lower())
        _shares_cache["data"] = results
        _shares_cache["ts"] = now
        return results
    except Exception as e:
        print(f"❌ [FS] Error al obtener carpetas compartidas: {e}")
        raise ValueError(f"Error de conexión con el Servidor de Archivos: {e}")


# ══════════════════════════════════════════════════════════════
# PERMISOS DE SHARE
# ══════════════════════════════════════════════════════════════

def get_folder_permissions(share_name: str):
    """
    Obtiene los permisos de compartición (Share Permissions) para una carpeta.
    """
    try:
        c = _get_wmi_connection()

        permissions = []

        sec_settings = c.Win32_LogicalShareSecuritySetting(Name=share_name)

        if not sec_settings:
            return permissions

        method_result = sec_settings[0].GetSecurityDescriptor()
        if method_result[0] != 0:
            print(f"⚠️ [FS] No se pudo leer el descriptor para {share_name}")
            return permissions

        sd = method_result[1]

        if hasattr(sd, "DACL") and sd.DACL:
            for dacl in sd.DACL:
                trustee = dacl.Trustee
                domain = trustee.Domain if hasattr(trustee, "Domain") and trustee.Domain else ""
                name = trustee.Name if hasattr(trustee, "Name") and trustee.Name else "Unknown"

                access_mask = getattr(dacl, "AccessMask", 0)

                permission_str = "Lectura"
                if access_mask == 2032127:
                    permission_str = "Control Total"
                elif access_mask == 1245631 or access_mask == 1245615:
                    permission_str = "Modificar"
                elif access_mask == 1179817 or access_mask == 1179785:
                    permission_str = "Lectura"
                else:
                    permission_str = f"Personalizado ({access_mask})"

                full_name = f"{domain}\\{name}" if domain else name

                permissions.append({
                    "account": full_name,
                    "access": permission_str,
                    "mask": access_mask
                })

        return permissions
    except Exception as e:
        print(f"❌ [FS] Error al obtener permisos de {share_name}: {e}")
        raise ValueError(f"Error al leer permisos: {e}")


# ══════════════════════════════════════════════════════════════
# NAVEGADOR DE ARCHIVOS
# ══════════════════════════════════════════════════════════════

def browse_folder(share_name: str, subpath: str = ""):
    """Navega por una carpeta compartida a través de su ruta UNC."""
    ip = authenticate_smb()

    clean_subpath = subpath.replace("/", "\\").strip("\\")
    if clean_subpath:
        target_path = f"\\\\{ip}\\{share_name}\\{clean_subpath}"
    else:
        target_path = f"\\\\{ip}\\{share_name}"

    if not os.path.exists(target_path):
        raise ValueError(f"La ruta no existe o no es accesible: {target_path}")

    items = []
    try:
        # Si la ruta es un archivo, devolvemos su info sin intentar escanearlo como directorio
        if os.path.isfile(target_path):
            stat_info = os.stat(target_path)
            return [{
                "name": os.path.basename(target_path),
                "is_dir": False,
                "size": stat_info.st_size,
                "modified_at": datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            }]

        with os.scandir(target_path) as it:
            for entry in it:
                is_dir = entry.is_dir()
                stat_info = entry.stat()

                # Ignorar archivos ocultos/sistema
                if entry.name.startswith('$') or entry.name == 'System Volume Information':
                    continue

                items.append({
                    "name": entry.name,
                    "is_dir": is_dir,
                    "size": stat_info.st_size if not is_dir else 0,
                    "modified_at": datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                })

        # Ordenar: primero carpetas, luego archivos, ambos alfabéticamente
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return items
    except PermissionError:
        raise ValueError("Acceso denegado a esta carpeta.")
    except Exception as e:
        raise ValueError(f"Error al leer carpeta: {str(e)}")
