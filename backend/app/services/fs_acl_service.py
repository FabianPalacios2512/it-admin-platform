"""
Servicio de ACL (permisos NTFS) para el Servidor de Archivos.
Usa PowerShell local con rutas UNC para LEER permisos,
y el comando nativo icacls para ESCRIBIR permisos (más confiable por red).
Resuelve SIDs a nombres amigables consultando el AD por LDAP.
"""
import subprocess
import json
import struct
from app.core.config import get_primary_server
from app.services.fs_service import authenticate_smb


# ══════════════════════════════════════════════════════════════
# RESOLUCIÓN DE NOMBRES
# ══════════════════════════════════════════════════════════════

def _sid_string_to_ldap_filter(sid_string: str) -> str:
    """Convierte un SID en formato string (S-1-5-21-...) a formato binario escapado para LDAP."""
    parts = sid_string.split('-')
    revision = int(parts[1])
    authority = int(parts[2])
    sub_authorities = [int(x) for x in parts[3:]]

    binary = struct.pack('BB', revision, len(sub_authorities))
    binary += struct.pack('>Q', authority)[2:]  # 6 bytes big-endian
    for sa in sub_authorities:
        binary += struct.pack('<I', sa)  # 4 bytes little-endian

    return ''.join(f'\\{b:02x}' for b in binary)


def _resolve_sid_via_ldap(sid_string: str) -> str:
    """Busca un SID en el Directorio Activo por LDAP y devuelve el nombre amigable."""
    try:
        from app.services.ad_service import _get_admin_connection, _get_search_base
        from ldap3 import SUBTREE

        conn = _get_admin_connection()
        search_base = _get_search_base()
        escaped_sid = _sid_string_to_ldap_filter(sid_string)

        conn.search(
            search_base=search_base,
            search_filter=f"(objectSid={escaped_sid})",
            search_scope=SUBTREE,
            attributes=['cn', 'displayName', 'sAMAccountName', 'objectClass']
        )

        if conn.entries:
            entry = conn.entries[0]
            sam = str(entry.sAMAccountName) if entry.sAMAccountName else ""
            display = str(entry.displayName) if entry.displayName else str(entry.cn) if entry.cn else sam
            object_classes = [str(c).lower() for c in entry.objectClass]

            # Obtener dominio NetBIOS
            da_cfg = get_primary_server("da")
            netbios = da_cfg["domain"].split(".")[0].upper()

            conn.unbind()

            if "group" in object_classes:
                return f"{display} ({netbios}\\{sam})"
            else:
                return f"{display} ({netbios}\\{sam})"

        conn.unbind()
    except Exception as e:
        print(f"⚠️ [ACL] No se pudo resolver SID {sid_string}: {e}")

    return sid_string  # Si no se pudo resolver, devolver el SID tal cual


def _resolve_account_name(raw_account: str) -> str:
    """Traduce una cuenta en bruto a un nombre amigable."""

    # Si es un SID, resolverlo por LDAP
    if raw_account.startswith("S-1-"):
        return _resolve_sid_via_ldap(raw_account)

    # Traducir cuentas BUILTIN y del sistema a nombres legibles
    builtin_map = {
        "BUILTIN\\Administradores": "Administradores (Local)",
        "BUILTIN\\Administrators": "Administradores (Local)",
        "BUILTIN\\Usuarios": "Usuarios (Local)",
        "BUILTIN\\Users": "Usuarios (Local)",
        "CREATOR OWNER": "CREATOR OWNER",
        "NT AUTHORITY\\SYSTEM": "SISTEMA",
        "NT AUTHORITY\\Authenticated Users": "Usuarios Autenticados",
    }

    if raw_account in builtin_map:
        return builtin_map[raw_account]

    # Si es BUILTIN o cuenta del hostname, simplificar
    if raw_account.startswith("BUILTIN\\"):
        name = raw_account.split("\\")[1]
        return f"{name} (Local)"

    # Si es una cuenta de dominio (DOMINIO\usuario), buscar en AD
    if '\\' in raw_account:
        domain, username = raw_account.split('\\', 1)
        # Si el dominio parece un hostname largo (ej. WIN-0VI60UL1QEV), es cuenta local
        if len(domain) > 10 and domain.startswith("WIN-"):
            return f"{username} ({domain})"
        # Buscar en AD
        try:
            from app.services.ad_service import _get_admin_connection, _get_search_base
            from ldap3 import SUBTREE

            conn = _get_admin_connection()
            search_base = _get_search_base()
            conn.search(
                search_base=search_base,
                search_filter=f"(sAMAccountName={username})",
                search_scope=SUBTREE,
                attributes=['displayName', 'cn', 'sAMAccountName']
            )
            if conn.entries:
                entry = conn.entries[0]
                display = str(entry.displayName) if entry.displayName else str(entry.cn) if entry.cn else username
                conn.unbind()
                return f"{display} ({domain}\\{username})"
            conn.unbind()
        except Exception:
            pass

    return raw_account


# ══════════════════════════════════════════════════════════════
# LECTURA DE ACL
# ══════════════════════════════════════════════════════════════

def _build_unc_path(share_name: str, subpath: str) -> str:
    """Construye la ruta UNC autenticada."""
    ip = authenticate_smb()
    clean = subpath.replace("/", "\\").strip("\\")
    if clean:
        return f"\\\\{ip}\\{share_name}\\{clean}"
    return f"\\\\{ip}\\{share_name}"


def get_acl(share_name: str, subpath: str = ""):
    """Obtiene los ACLs NTFS de una ruta usando PowerShell Get-Acl local con ruta UNC."""
    target_path = _build_unc_path(share_name, subpath)

    ps_script = f"""
    try {{
        $acl = Get-Acl -LiteralPath '{target_path}'
        $rules = @()
        foreach ($access in $acl.Access) {{
            $rules += @{{
                Account = $access.IdentityReference.Value
                Access = $access.FileSystemRights.ToString()
                Type = $access.AccessControlType.ToString()
                Inherited = $access.IsInherited
            }}
        }}
        $rules | ConvertTo-Json -Compress
    }} catch {{
        Write-Error $_.Exception.Message
        exit 1
    }}
    """

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True, timeout=15
    )

    if result.returncode != 0:
        raise ValueError(f"Error obteniendo permisos: {result.stderr.strip()}")

    try:
        output = result.stdout.strip()
        if not output:
            return []
        data = json.loads(output)
        if isinstance(data, dict):
            data = [data]

        # Deduplicar: agrupar por cuenta y si tienen mismo tipo (explícito/heredado)
        seen = set()
        clean_permissions = []

        for r in data:
            raw = r.get("Account", "")
            if not raw:
                continue

            raw_access = r.get("Access", "")
            inherited = r.get("Inherited", False)

            # Clave de deduplicación
            dedup_key = f"{raw}|{inherited}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            # Parsear nivel de acceso
            if "FullControl" in raw_access:
                access = "Control Total"
            elif "Modify" in raw_access:
                access = "Modificar"
            elif "ReadAndExecute" in raw_access:
                access = "Lectura y Ejecución"
            elif "Read" in raw_access:
                access = "Lectura"
            elif "Write" in raw_access:
                access = "Escritura"
            else:
                access = "Especial"

            # Resolver nombre amigable
            friendly = _resolve_account_name(raw)

            clean_permissions.append({
                "account": friendly,
                "raw_account": raw,
                "access": access,
                "raw_access": raw_access,
                "type": r.get("Type", "Allow"),
                "inherited": inherited
            })

        return clean_permissions

    except json.JSONDecodeError:
        print(f"⚠️ [ACL] Error parseando JSON: {result.stdout[:200]}")
        return []


# ══════════════════════════════════════════════════════════════
# ESCRITURA DE ACL
# Ejecutamos icacls REMOTAMENTE en el servidor de archivos
# usando WMI (Win32_Process.Create), así el servidor resuelve
# las cuentas del dominio sin problemas.
# ══════════════════════════════════════════════════════════════

_PERMISSION_MAP = {
    "ReadAndExecute": "(OI)(CI)(RX)",
    "Modify": "(OI)(CI)(M)",
    "FullControl": "(OI)(CI)(F)",
    "Read": "(OI)(CI)(R)",
}


def _run_remote_icacls(icacls_args: str) -> str:
    """
    Ejecuta un comando icacls REMOTAMENTE en el servidor de archivos via WMI.
    Usa Win32_Process.Create para lanzar el proceso en el servidor,
    redirige la salida a un archivo temporal, y lo lee de vuelta por UNC (C$).
    """
    import wmi
    import pythoncom
    import uuid
    import time

    cfg = get_primary_server("files")
    ip = cfg["ip"]
    user = cfg["admin_user"]
    password = cfg["admin_pass"]

    # Autenticar SMB para acceder a C$ del servidor
    authenticate_smb()
    # También autenticar contra el admin share
    c_share = f"\\\\{ip}\\C$"
    subprocess.run(["net", "use", c_share, "/delete"], capture_output=True)
    net_user = user if '\\' in user else f"{cfg.get('domain', 'code.local').split('.')[0]}\\{user}"
    subprocess.run(["net", "use", c_share, password, f"/user:{net_user}"], capture_output=True, text=True)

    # Archivo temporal para capturar output
    temp_id = uuid.uuid4().hex[:8]
    remote_temp_file = f"C:\\Windows\\Temp\\acl_{temp_id}.txt"
    unc_temp_file = f"\\\\{ip}\\C$\\Windows\\Temp\\acl_{temp_id}.txt"

    # El comando completo que se ejecutará EN el servidor
    full_cmd = f'cmd /c "icacls {icacls_args} > {remote_temp_file} 2>&1"'

    print(f"🔧 [ACL] Ejecutando remotamente en {ip}: icacls {icacls_args}")

    try:
        pythoncom.CoInitialize()
        try:
            c = wmi.WMI(computer=ip, user=user, password=password)
        except Exception as e:
            if "local connections" in str(e):
                c = wmi.WMI()
            else:
                raise

        # Crear proceso remoto
        process_id, return_value = c.Win32_Process.Create(CommandLine=full_cmd)

        if return_value != 0:
            raise ValueError(f"WMI Win32_Process.Create falló con código {return_value}")

        # Esperar a que el proceso termine (máx 10 segundos)
        for _ in range(20):
            time.sleep(0.5)
            try:
                with open(unc_temp_file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().strip()
                    if content:  # El archivo tiene contenido, el proceso terminó
                        break
            except (FileNotFoundError, PermissionError):
                continue

        # Leer el resultado
        output = ""
        try:
            with open(unc_temp_file, "r", encoding="utf-8", errors="replace") as f:
                output = f.read().strip()
        except Exception:
            pass

        # Limpiar archivo temporal
        try:
            import os
            os.remove(unc_temp_file)
        except Exception:
            pass

        return output

    except Exception as e:
        raise ValueError(f"Error ejecutando comando remoto en el servidor: {e}")


def _get_share_local_path(share_name: str) -> str:
    """Obtiene la ruta local de un share en el servidor (ej: C:\\Empresa_Files)."""
    import wmi
    import pythoncom

    cfg = get_primary_server("files")
    pythoncom.CoInitialize()
    try:
        c = wmi.WMI(computer=cfg["ip"], user=cfg["admin_user"], password=cfg["admin_pass"])
    except Exception as e:
        if "local connections" in str(e):
            c = wmi.WMI()
        else:
            raise

    shares = c.Win32_Share(Name=share_name)
    if not shares:
        raise ValueError(f"Share '{share_name}' no encontrado en el servidor.")

    return shares[0].Path


def add_acl(share_name: str, subpath: str, account: str, permission_level: str):
    """
    Agrega un permiso NTFS ejecutando icacls REMOTAMENTE en el servidor de archivos.
    """
    share_path = _get_share_local_path(share_name)
    clean_subpath = subpath.replace("/", "\\").strip("\\")
    target_path = f"{share_path}\\{clean_subpath}" if clean_subpath else share_path

    if permission_level == "Deny":
        icacls_args = f'"{target_path}" /deny "{account}:(OI)(CI)(F)"'
    else:
        perm_flag = _PERMISSION_MAP.get(permission_level, "(OI)(CI)(RX)")
        icacls_args = f'"{target_path}" /grant "{account}:{perm_flag}"'

    output = _run_remote_icacls(icacls_args)
    
    if "correctamente" in output.lower() or "processed" in output.lower() or "procesado" in output.lower():
        print(f"✅ [ACL] Permiso agregado: {account} -> {permission_level} en {target_path}")
        
        # INYECCIÓN DE TRÁNSITO EN LA RAÍZ DEL SHARE (This Folder Only)
        # Solo se aplica si estamos asignando permiso a una subcarpeta y NO es Deny.
        if clean_subpath and permission_level != "Deny":
            print(f"🔧 [ACL] Inyectando permiso de Tránsito (RX) en padre {share_path}")
            # (RX) sin (OI)(CI) aplica solo a la carpeta padre.
            icacls_transit = f'"{share_path}" /grant "{account}:(RX)"'
            _run_remote_icacls(icacls_transit)
            
        return True
    else:
        raise ValueError(f"Error aplicando permisos: {output}")


def _extract_raw_ntaccount(account: str) -> str:
    """
    Extrae la cuenta NTAccount pura de un nombre amigable o SID.
    Ej: 'Fabian Paternina (CODE\\fapaternina)' -> 'CODE\\fapaternina'
    Ej: 'S-1-5-21-...' -> 'CODE\\fapaternina'  (resuelve por LDAP)
    Ej: 'CODE\\fapaternina' -> 'CODE\\fapaternina'  (ya está limpio)
    """
    import re

    # Si es un SID, intentar resolverlo a NTAccount vía LDAP
    if account.startswith("S-1-"):
        try:
            from app.services.ad_service import _get_admin_connection, _get_search_base
            from ldap3 import SUBTREE

            escaped_sid = _sid_string_to_ldap_filter(account)
            conn = _get_admin_connection()
            conn.search(
                search_base=_get_search_base(),
                search_filter=f"(objectSid={escaped_sid})",
                search_scope=SUBTREE,
                attributes=['sAMAccountName']
            )
            if conn.entries:
                sam = str(conn.entries[0].sAMAccountName)
                da_cfg = get_primary_server("da")
                netbios = da_cfg["domain"].split(".")[0].upper()
                conn.unbind()
                return f"{netbios}\\{sam}"
            conn.unbind()
        except Exception as e:
            print(f"⚠️ [ACL] No se pudo resolver SID {account}: {e}")
        # Fallback: devolver con asterisco para icacls
        return f"*{account}"

    # Buscar patrón (DOMINIO\usuario) dentro del string
    match = re.search(r'\(([^)\\]+\\[^)]+)\)', account)
    if match:
        return match.group(1)

    # Si ya tiene formato DOMINIO\usuario, dejarlo
    if '\\' in account:
        return account

    return account


def remove_acl(share_name: str, subpath: str, account: str):
    """
    Remueve todos los permisos de una cuenta ejecutando icacls REMOTAMENTE.
    """
    clean_account = _extract_raw_ntaccount(account)

    share_path = _get_share_local_path(share_name)
    clean_subpath = subpath.replace("/", "\\").strip("\\")
    target_path = f"{share_path}\\{clean_subpath}" if clean_subpath else share_path

    print(f"🔧 [ACL] Eliminando permisos de '{clean_account}' en {target_path}")

    # /remove:g quita entradas Grant, /remove:d quita entradas Deny
    icacls_args = f'"{target_path}" /remove:g "{clean_account}"'

    output = _run_remote_icacls(icacls_args)

    if "correctamente" in output.lower() or "processed" in output.lower() or "procesado" in output.lower():
        print(f"✅ [ACL] Permiso eliminado: {clean_account} de {target_path}")
        return True
    else:
        raise ValueError(f"Error eliminando permisos: {output}")


def disable_inheritance_and_copy(share_name: str, subpath: str):
    """
    Deshabilita la herencia de NTFS pero mantiene una copia explícita de los permisos heredados.
    """
    share_path = _get_share_local_path(share_name)
    clean_subpath = subpath.replace("/", "\\").strip("\\")
    target_path = f"{share_path}\\{clean_subpath}" if clean_subpath else share_path

    print(f"🔧 [ACL] Deshabilitando herencia (Copia) en {target_path}")

    # /inheritance:d copia permisos heredados a explícitos
    icacls_args = f'"{target_path}" /inheritance:d'
    output = _run_remote_icacls(icacls_args)

    if "correctamente" in output.lower() or "processed" in output.lower() or "procesado" in output.lower():
        print(f"✅ [ACL] Herencia deshabilitada en {target_path}")
        return True
    else:
        raise ValueError(f"Error rompiendo herencia: {output}")

def get_user_effective_folders(username: str):
    """
    Escanea el Servidor de Archivos (Shares y subcarpetas nivel 1)
    para encontrar a qué carpetas tiene acceso el usuario, ya sea directamente
    o a través de sus grupos de AD (usando SIDs y Nombres).
    """
    from app.services.ad_service import _get_admin_connection, _get_search_base
    from ldap3 import SUBTREE
    from app.services.fs_service import get_shared_folders, browse_folder, authenticate_smb
    from app.core.config import get_primary_server
    import json
    import subprocess
    
    conn = _get_admin_connection()
    search_base = _get_search_base()
    
    # 1. Obtener SID del usuario y sus grupos
    conn.search(
        search_base=search_base,
        search_filter=f"(sAMAccountName={username})",
        search_scope=SUBTREE,
        attributes=['sAMAccountName', 'memberOf', 'objectSid']
    )
    if not conn.entries:
        conn.unbind()
        return []
        
    user_entry = conn.entries[0]
    user_sam = str(user_entry.sAMAccountName)
    user_sid = str(user_entry.objectSid.value) if 'objectSid' in user_entry else ""
    
    da_cfg = get_primary_server("da")
    netbios = da_cfg["domain"].split(".")[0].upper()
    
    user_identities = set()
    user_identities.add(f"{netbios}\\{user_sam}".lower())
    if user_sid:
        user_identities.add(user_sid.lower())
    
    # Mapeo de SIDs a Nombres de grupo para mostrar en la UI
    sid_to_name = {user_sid.lower(): f"{netbios}\\{user_sam}"}
    
    if user_entry.memberOf:
        for group_dn in user_entry.memberOf:
            group_name = str(group_dn).split(",")[0].replace("CN=", "")
            user_identities.add(f"{netbios}\\{group_name}".lower())
            
            # Buscar el SID del grupo
            conn.search(
                search_base=search_base,
                search_filter=f"(distinguishedName={group_dn})",
                search_scope=SUBTREE,
                attributes=['objectSid']
            )
            if conn.entries and 'objectSid' in conn.entries[0]:
                g_sid = str(conn.entries[0].objectSid.value).lower()
                user_identities.add(g_sid)
                sid_to_name[g_sid] = f"{netbios}\\{group_name}"
            
    conn.unbind()

    paths_to_scan = []
    try:
        shares = get_shared_folders()
        ip = authenticate_smb()
        
        for share in shares:
            share_unc = f"\\\\{ip}\\{share['name']}"
            paths_to_scan.append({
                "path": share_unc, 
                "share": share['name'], 
                "folder": ""
            })
            
            try:
                items = browse_folder(share['name'], "")
                for item in items:
                    if item["is_dir"]:
                        paths_to_scan.append({
                            "path": f"{share_unc}\\{item['name']}",
                            "share": share['name'],
                            "folder": item['name']
                        })
            except Exception:
                pass
    except Exception as e:
        print(f"❌ [FS] Error obteniendo rutas para escaneo de usuario: {e}")
        return []

    if not paths_to_scan:
        return []

    ps_paths = ",".join([f"'{p['path']}'" for p in paths_to_scan])
    
    ps_script = f"""
    $paths = @({ps_paths})
    $results = @()
    
    foreach ($p in $paths) {{
        try {{
            $acl = Get-Acl -LiteralPath $p -ErrorAction SilentlyContinue
            if ($acl) {{
                foreach ($access in $acl.Access) {{
                    $results += @{{
                        Path = $p
                        Account = $access.IdentityReference.Value
                        Access = $access.FileSystemRights.ToString()
                        Type = $access.AccessControlType.ToString()
                        Inherited = $access.IsInherited
                    }}
                }}
            }}
        }} catch {{ }}
    }}
    $results | ConvertTo-Json -Compress
    """
    
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True, timeout=60
    )
    
    assigned_folders = []
    
    if result.returncode == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout.strip())
            if isinstance(data, dict):
                data = [data]
                
            for rule in data:
                if rule.get("Type") == "Allow":
                    account = rule.get("Account", "").lower()
                    
                    if account in user_identities:
                        raw_access = rule.get("Access", "")
                        if "FullControl" in raw_access:
                            access_str = "Control Total"
                        elif "Modify" in raw_access:
                            access_str = "Modificar"
                        elif "ReadAndExecute" in raw_access:
                            inheritance_type = rule.get("InheritanceFlags", "None")
                            inherited_flag = rule.get("Inherited", False)
                            # Si es explícito y InheritanceFlags es None (solo aplica a esta carpeta)
                            if inheritance_type == "None" and not inherited_flag:
                                access_str = "Tránsito / Solo Lectura (Explícito)"
                            else:
                                access_str = "Lectura y Ejecución"
                        elif "Read" in raw_access:
                            access_str = "Lectura"
                        elif "Write" in raw_access:
                            access_str = "Escritura"
                        else:
                            access_str = "Especial"
                            
                        is_direct = account == f"{netbios}\\{user_sam}".lower() or account == user_sid.lower()
                        
                        # Capitalizamos el origen para mostrar bonito en la UI
                        display_account = sid_to_name.get(account, rule.get("Account"))
                        origin = f"Explícito ({display_account})" if is_direct else f"Heredado por grupo ({display_account})"
                        
                        unc_path = rule.get("Path", "")
                        # Quitar \\IP\ para mostrar ej: Empresa_Files\Gerencia
                        display_path = unc_path.replace(f"\\\\{ip}\\", "").replace("\\", "/")
                        
                        existing = next((f for f in assigned_folders if f["path"] == display_path), None)
                        if not existing:
                            assigned_folders.append({
                                "path": display_path,
                                "access": access_str,
                                "origin": origin,
                                "inherited": rule.get("Inherited", False)
                            })
                        else:
                            levels = {"Control Total": 4, "Modificar": 3, "Escritura": 2, "Lectura y Ejecución": 1, "Tránsito / Solo Lectura (Explícito)": 1, "Lectura": 0, "Especial": -1}
                            current_level = levels.get(existing["access"], -1)
                            new_level = levels.get(access_str, -1)
                            
                            # Combine origins if they differ
                            if existing["origin"] != origin and origin not in existing["origin"]:
                                existing["origin"] = f'{existing["origin"]} / {origin}'
                                
                            if new_level > current_level:
                                existing["access"] = access_str
                                existing["inherited"] = rule.get("Inherited", False)
                            elif new_level == current_level and not rule.get("Inherited", False) and existing["inherited"]:
                                # Prefer explicit over inherited when levels are equal
                                existing["inherited"] = False
        except Exception as e:
            print(f"❌ [FS] Error parseando ACLs en lote: {e}")
            
    assigned_paths = {f["path"] for f in assigned_folders}
    
    # Agregar carpetas analizadas pero sin acceso
    for p in paths_to_scan:
        display_path = p["path"].replace(f"\\\\{ip}\\", "").replace("\\", "/")
        if display_path not in assigned_paths:
            assigned_folders.append({
                "path": display_path,
                "access": "Sin Acceso",
                "origin": "No asignado",
                "inherited": False
            })
            assigned_paths.add(display_path)

    # Ordenar alfabéticamente
    assigned_folders.sort(key=lambda x: x["path"])
    return assigned_folders


def get_user_effective_folders_debug(username: str):
    from app.services.ad_service import _get_admin_connection, _get_search_base
    from ldap3 import SUBTREE
    from app.services.fs_service import get_shared_folders, browse_folder, authenticate_smb
    from app.core.config import get_primary_server
    import json
    import subprocess
    
    conn = _get_admin_connection()
    search_base = _get_search_base()
    
    conn.search(
        search_base=search_base,
        search_filter=f"(sAMAccountName={username})",
        search_scope=SUBTREE,
        attributes=['sAMAccountName', 'memberOf']
    )
    if not conn.entries:
        conn.unbind()
        return {"error": "User not found"}
        
    user_entry = conn.entries[0]
    user_sam = str(user_entry.sAMAccountName)
    
    da_cfg = get_primary_server("da")
    netbios = da_cfg["domain"].split(".")[0].upper()
    
    user_identities = set()
    user_identities.add(f"{netbios}\\{user_sam}".lower())
    
    if user_entry.memberOf:
        for group_dn in user_entry.memberOf:
            group_name = str(group_dn).split(",")[0].replace("CN=", "")
            user_identities.add(f"{netbios}\\{group_name}".lower())
            
    conn.unbind()

    paths_to_scan = []
    try:
        shares = get_shared_folders()
        ip = authenticate_smb()
        
        for share in shares:
            share_unc = f"\\\\{ip}\\{share['name']}"
            paths_to_scan.append({
                "path": share_unc, 
                "share": share['name'], 
                "folder": ""
            })
            
            try:
                items = browse_folder(share['name'], "")
                for item in items:
                    if item["is_dir"]:
                        paths_to_scan.append({
                            "path": f"{share_unc}\\{item['name']}",
                            "share": share['name'],
                            "folder": item['name']
                        })
            except Exception:
                pass
    except Exception as e:
        return {"error": str(e), "step": "scan"}

    if not paths_to_scan:
        return {"error": "no paths to scan"}

    ps_paths = ",".join([f"'{p['path']}'" for p in paths_to_scan])
    
    ps_script = f"""
    $paths = @({ps_paths})
    $results = @()
    
    foreach ($p in $paths) {{
        try {{
            $acl = Get-Acl -LiteralPath $p -ErrorAction SilentlyContinue
            if ($acl) {{
                foreach ($access in $acl.Access) {{
                    $results += @{{
                        Path = $p
                        Account = $access.IdentityReference.Value
                        Access = $access.FileSystemRights.ToString()
                        Type = $access.AccessControlType.ToString()
                        Inherited = $access.IsInherited
                    }}
                }}
            }}
        }} catch {{ }}
    }}
    $results | ConvertTo-Json -Compress
    """
    
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True, timeout=60
    )
    
    data = None
    if result.returncode == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout.strip())
        except Exception:
            data = result.stdout.strip()
    
    return {
        "identities": list(user_identities),
        "powershell_stdout": data,
        "powershell_stderr": result.stderr
    }

def create_folder(share_name: str, subpath: str, folder_name: str, inherit_permissions: bool = True):
    from app.services.fs_service import authenticate_smb
    import subprocess
    import json
    
    ip = authenticate_smb()
    unc_base_path = _build_unc_path(share_name, subpath)
    unc_new_folder = f"{unc_base_path}\\{folder_name}"
    
    # PowerShell script para crear la carpeta y manejar la herencia
    ps_script = f"""
    try {{
        $newFolder = New-Item -Path '{unc_new_folder}' -ItemType Directory -ErrorAction Stop
        
        if ($false -eq ${str(inherit_permissions).lower()}) {{
            # Desactivar la herencia de la nueva carpeta
            $acl = Get-Acl -LiteralPath '{unc_new_folder}'
            $acl.SetAccessRuleProtection($true, $false) # (isProtected, preserveInheritance)
            Set-Acl -LiteralPath '{unc_new_folder}' -AclObject $acl
        }}
        
        Write-Output ( [PSCustomObject]@{{ success=$true }} | ConvertTo-Json -Compress )
    }} catch {{
        Write-Output ( [PSCustomObject]@{{ success=$false; error=$_.Exception.Message }} | ConvertTo-Json -Compress )
    }}
    """
    
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True, timeout=30
    )
    
    try:
        data = json.loads(result.stdout.strip())
        if not data.get("success"):
            raise ValueError(data.get("error", "Error desconocido creando carpeta"))
    except json.JSONDecodeError:
        raise ValueError(f"Error ejecutando PowerShell: {result.stderr or result.stdout}")

def audit_effective_access(share_name: str, subpath: str):
    from app.services.fs_service import authenticate_smb
    import subprocess
    import json
    
    ip = authenticate_smb()
    unc_path = _build_unc_path(share_name, subpath)
    
    ps_script = f"""
    try {{
        $acl = Get-Acl -LiteralPath '{unc_path}' -ErrorAction Stop
        $results = @()
        foreach ($access in $acl.Access) {{
            $results += @{{
                Account = $access.IdentityReference.Value
                Access = $access.FileSystemRights.ToString()
                Type = $access.AccessControlType.ToString()
                Inherited = $access.IsInherited
            }}
        }}
        Write-Output ( @{{ success=$true; data=$results }} | ConvertTo-Json -Depth 10 -Compress )
    }} catch {{
        Write-Output ( @{{ success=$false; error=$_.Exception.Message }} | ConvertTo-Json -Compress )
    }}
    """
    
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True, timeout=60
    )
    
    try:
        data = json.loads(result.stdout.strip())
        if not data.get("success"):
            raise ValueError(data.get("error", "Error desconocido en Get-Acl"))
        return data.get("data", [])
    except json.JSONDecodeError:
        raise ValueError(f"Error ejecutando PowerShell: {result.stderr or result.stdout}")
