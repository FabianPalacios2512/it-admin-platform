"""
Servicio central de Active Directory.
Usa la Cuenta de Servicio (Service Account) para TODAS las consultas.
Obtiene la configuración del servidor dinámicamente desde la DB.
"""
from ldap3 import Server, Connection, ALL, SUBTREE, MODIFY_REPLACE
from ldap3.core.exceptions import LDAPException
from app.core.config import settings, get_primary_server
import time

def _get_admin_connection():
    """Abre una conexión LDAP usando el servidor primario configurado."""
    cfg = get_primary_server("da")
    server = Server(cfg["ip"], get_info=ALL)
    conn = Connection(server, user=cfg["admin_user"], password=cfg["admin_pass"], auto_bind=True)
    return conn


def _get_search_base():
    cfg = get_primary_server("da")
    domain = cfg["domain"]
    return f"DC={domain.replace('.', ',DC=')}"


def _parse_ad_timestamp(val):
    """Convierte un timestamp de AD (Windows FileTime o datetime) a string legible."""
    if val is None:
        return "N/A"
    # ldap3 ya convierte a datetime en la mayoría de los casos
    try:
        return val.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(val)

def _paged_search(conn, search_base, search_filter, attributes, limit=None):
    from ldap3 import SUBTREE
    entries = []
    cookie = None
    while True:
        conn.search(
            search_base=search_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=attributes,
            paged_size=1000,
            paged_cookie=cookie
        )
        entries.extend(conn.entries)
        
        if limit and len(entries) >= limit:
            entries = entries[:limit]
            break
            
        controls = conn.result.get('controls', {})
        paged_ctrl = controls.get('1.2.840.113556.1.4.319', {})
        value = paged_ctrl.get('value', {})
        cookie = value.get('cookie')
        if not cookie:
            break
    return entries


# ══════════════════════════════════════════════════════════════
# BÚSQUEDA DE USUARIOS
# ══════════════════════════════════════════════════════════════
def search_users(query: str, limit: int = 20) -> list:
    """
    Busca usuarios en el AD por nombre, sAMAccountName o correo.
    Retorna una lista de diccionarios con datos básicos.
    """
    conn = _get_admin_connection()
    search_base = _get_search_base()

    # Filtro LDAP: busca en displayName, sAMAccountName y mail
    safe_query = query.replace("(", "").replace(")", "").replace("*", "").replace("\\", "").strip()
    
    if not safe_query:
        search_filter = "(&(objectCategory=person)(objectClass=user))"
    else:
        search_filter = (
            f"(&(objectCategory=person)(objectClass=user)"
            f"(|(displayName=*{safe_query}*)(sAMAccountName=*{safe_query}*)(mail=*{safe_query}*)))"
        )

    entries = _paged_search(
        conn=conn,
        search_base=search_base,
        search_filter=search_filter,
        attributes=['sAMAccountName', 'displayName', 'title', 'mail', 'department', 'userAccountControl', 'distinguishedName', 'userPrincipalName'],
        limit=limit
    )

    results = []
    for entry in entries:
        uac = int(str(entry.userAccountControl)) if entry.userAccountControl else 0
        is_disabled = bool(uac & 0x0002)
        is_locked = bool(uac & 0x0010)

        status = "active"
        if is_locked:
            status = "locked"
        elif is_disabled:
            status = "disabled"

        ou_name = ""
        if entry.distinguishedName:
            dn_str = str(entry.distinguishedName)
            parts = dn_str.split(",")
            for part in parts:
                if part.strip().upper().startswith("OU="):
                    ou_name = part.strip()[3:]
                    break

        results.append({
            "username": str(entry.sAMAccountName),
            "userPrincipalName": str(entry.userPrincipalName) if entry.userPrincipalName else "",
            "fullName": str(entry.displayName) if entry.displayName else str(entry.sAMAccountName),
            "title": str(entry.title) if entry.title else "",
            "email": str(entry.mail) if entry.mail else "",
            "department": str(entry.department) if entry.department else "",
            "ou": ou_name,
            "status": status,
            "dn": str(entry.distinguishedName) if entry.distinguishedName else "",
        })

    conn.unbind()
    return results


# ══════════════════════════════════════════════════════════════
# PERFIL 360 DE UN USUARIO
# ══════════════════════════════════════════════════════════════
def get_user_profile(username: str) -> dict | None:
    """
    Obtiene el perfil completo de un usuario del AD incluyendo grupos.
    """
    conn = _get_admin_connection()
    search_base = _get_search_base()

    search_filter = f"(sAMAccountName={username})"
    conn.search(
        search_base=search_base,
        search_filter=search_filter,
        search_scope=SUBTREE,
        attributes=[
            'sAMAccountName', 'displayName', 'givenName', 'sn',
            'title', 'mail', 'department', 'company', 'manager',
            'physicalDeliveryOfficeName', 'telephoneNumber', 'mobile',
            'whenCreated', 'pwdLastSet', 'lastLogon', 'lastLogonTimestamp',
            'userAccountControl', 'lockoutTime', 'badPwdCount',
            'memberOf', 'distinguishedName', 'description', 'proxyAddresses', 'userPrincipalName',
        ],
    )

    if not conn.entries:
        conn.unbind()
        return None

    entry = conn.entries[0]

    # Parsear userAccountControl flags
    uac = int(str(entry.userAccountControl)) if entry.userAccountControl else 0
    flags = []
    if uac & 0x0002:
        flags.append("ACCOUNT_DISABLED")
    if uac & 0x0010:
        flags.append("LOCKOUT")
    if uac & 0x0020:
        flags.append("NORMAL_ACCOUNT") if not (uac & 0x0020) else None
    if uac & 0x10000:
        flags.append("PASSWORD_NEVER_EXPIRES")
    if uac & 0x800000:
        flags.append("PASSWORD_EXPIRED")
    if not flags:
        flags.append("NORMAL_ACCOUNT")

    try:
        lockout_time_str = str(entry.lockoutTime) if entry.lockoutTime else "0"
        # Si ldap3 ya lo parseó como datetime, contendrá '-'
        if "-" in lockout_time_str:
            lockout_time = 0 if "1601" in lockout_time_str else 1
        else:
            lockout_time = int(lockout_time_str)
    except ValueError:
        lockout_time = 0

    is_locked = bool(lockout_time >= 1)
    is_disabled = bool(uac & 0x0002)

    status = "active"
    if is_locked:
        status = "locked"
    elif is_disabled:
        status = "disabled"

    # Parsear grupos (memberOf)
    groups = []
    if entry.memberOf:
        for group_dn in entry.memberOf:
            group_name = str(group_dn).split(",")[0].replace("CN=", "")
            groups.append({
                "name": group_name,
                "dn": str(group_dn),
            })

    # Parsear manager
    manager_name = ""
    if entry.manager:
        manager_dn = str(entry.manager)
        manager_name = manager_dn.split(",")[0].replace("CN=", "")

    profile = {
        "username": str(entry.sAMAccountName),
        "fullName": str(entry.displayName) if entry.displayName else str(entry.sAMAccountName),
        "firstName": str(entry.givenName) if entry.givenName else "",
        "lastName": str(entry.sn) if entry.sn else "",
        "userPrincipalName": str(entry.userPrincipalName) if entry.userPrincipalName else "",
        "title": str(entry.title) if entry.title else "",
        "email": str(entry.mail) if entry.mail else "",
        "department": str(entry.department) if entry.department else "",
        "company": str(entry.company) if entry.company else "",
        "manager": manager_name,
        "office": str(entry.physicalDeliveryOfficeName) if entry.physicalDeliveryOfficeName else "",
        "phone": str(entry.telephoneNumber) if entry.telephoneNumber else "",
        "mobile": str(entry.mobile) if entry.mobile else "",
        "description": str(entry.description) if entry.description else "",
        "distinguishedName": str(entry.distinguishedName),
        "status": status,
        "flags": flags,
        "groups": groups,
        "badPwdCount": int(str(entry.badPwdCount)) if entry.badPwdCount else 0,
        "created": _parse_ad_timestamp(entry.whenCreated.value if entry.whenCreated else None),
        "passwordLastSet": _parse_ad_timestamp(entry.pwdLastSet.value if entry.pwdLastSet else None),
        "lastLogon": _parse_ad_timestamp(entry.lastLogonTimestamp.value if entry.lastLogonTimestamp else None),
        "proxyAddresses": [str(addr) for addr in entry.proxyAddresses] if entry.proxyAddresses else [],
    }

    conn.unbind()
    return profile


# ══════════════════════════════════════════════════════════════
# CUENTAS BLOQUEADAS
# ══════════════════════════════════════════════════════════════
def get_locked_accounts() -> list:
    """Busca todas las cuentas bloqueadas en el AD."""
    conn = _get_admin_connection()
    search_base = _get_search_base()

    # lockoutTime > 0 indica que la cuenta está bloqueada
    search_filter = "(&(objectCategory=person)(objectClass=user)(lockoutTime>=1))"
    entries = _paged_search(
        conn=conn,
        search_base=search_base,
        search_filter=search_filter,
        attributes=[
            'sAMAccountName', 'displayName', 'mail', 'department',
            'manager', 'lockoutTime', 'badPwdCount', 'lastLogon',
            'distinguishedName', 'userAccountControl', 'memberOf',
        ]
    )

    results = []
    for entry in entries:
        manager_name = ""
        if entry.manager:
            manager_name = str(entry.manager).split(",")[0].replace("CN=", "")

        # Parsear flags
        uac = int(str(entry.userAccountControl)) if entry.userAccountControl else 0
        flags = []
        if uac & 0x0002:
            flags.append("ACCOUNT_DISABLED")
        if uac & 0x0010:
            flags.append("LOCKOUT")
        if uac & 0x10000:
            flags.append("PASSWORD_NEVER_EXPIRES")
        flags.append("NORMAL_ACCOUNT")

        results.append({
            "username": str(entry.sAMAccountName),
            "fullName": str(entry.displayName) if entry.displayName else str(entry.sAMAccountName),
            "email": str(entry.mail) if entry.mail else "",
            "department": str(entry.department) if entry.department else "",
            "manager": manager_name,
            "badPwdCount": int(str(entry.badPwdCount)) if entry.badPwdCount else 0,
            "lockoutTime": _parse_ad_timestamp(entry.lockoutTime.value if entry.lockoutTime else None),
            "lastLogon": _parse_ad_timestamp(entry.lastLogon.value if entry.lastLogon else None),
            "distinguishedName": str(entry.distinguishedName),
            "flags": flags,
        })

    conn.unbind()
    return results


# ══════════════════════════════════════════════════════════════
# ESTADÍSTICAS DE SALUD DEL AD
# ══════════════════════════════════════════════════════════════
_ad_health_stats_cache = {"time": 0, "data": None}
_CACHE_TTL = 30

def get_ad_health_stats() -> dict:
    """Obtiene estadísticas de salud del AD: cuentas activas, inactivas, etc."""
    global _ad_health_stats_cache
    if time.time() - _ad_health_stats_cache["time"] < _CACHE_TTL and _ad_health_stats_cache["data"]:
        return _ad_health_stats_cache["data"]

    conn = _get_admin_connection()
    search_base = _get_search_base()
    
    def count_query(ldap_filter):
        entries = _paged_search(
            conn=conn,
            search_base=search_base,
            search_filter=ldap_filter,
            attributes=['sAMAccountName']
        )
        return len(entries)

    total_users = count_query("(objectCategory=person)")
    disabled_users = count_query("(&(objectCategory=person)(userAccountControl:1.2.840.113556.1.4.803:=2))")
    enabled_users = total_users - disabled_users
    pwd_never_expires = count_query("(&(objectCategory=person)(userAccountControl:1.2.840.113556.1.4.803:=65536))")
    
    import datetime
    ninety_days_ago = datetime.datetime.now() - datetime.timedelta(days=90)
    # Timestamp a formato Windows FileTime (100-nanosecond intervals since Jan 1, 1601)
    file_time = int((ninety_days_ago.timestamp() + 11644473600) * 10000000)
    inactive_users = count_query(f"(&(objectCategory=person)(lastLogonTimestamp<={file_time})(lastLogonTimestamp>=1))")
    
    locked_users = count_query("(&(objectCategory=person)(lockoutTime>=1))")
    
    seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    when_created_str = seven_days_ago.strftime("%Y%m%d%H%M%S.0Z")
    new_computers = count_query(f"(&(objectCategory=computer)(whenCreated>={when_created_str}))")
    
    conn.unbind()
    
    result = {
        "total_users": total_users,
        "enabled_users": enabled_users,
        "disabled_users": disabled_users,
        "password_never_expires": pwd_never_expires,
        "inactive_users_90d": inactive_users,
        "locked_users": locked_users,
        "new_computers": new_computers,
    }
    
    _ad_health_stats_cache["time"] = time.time()
    _ad_health_stats_cache["data"] = result
    
    return result


# ══════════════════════════════════════════════════════════════
# DESBLOQUEAR CUENTA
# ══════════════════════════════════════════════════════════════
def unlock_account(username: str) -> dict:
    """Desbloquea una cuenta de AD estableciendo lockoutTime a 0."""
    conn = _get_admin_connection()
    search_base = _get_search_base()

    conn.search(search_base, f"(sAMAccountName={username})", SUBTREE, attributes=['distinguishedName'])
    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Usuario '{username}' no encontrado en el AD."}

    user_dn = str(conn.entries[0].distinguishedName)

    # Poner lockoutTime a 0 desbloquea la cuenta
    result = conn.modify(user_dn, {'lockoutTime': [(MODIFY_REPLACE, ['0'])]})

    if result:
        conn.unbind()
        return {"success": True, "message": f"Cuenta '{username}' desbloqueada exitosamente."}
    else:
        error = conn.result.get('description', 'Error desconocido')
        conn.unbind()
        return {"success": False, "error": f"No se pudo desbloquear: {error}"}


# ══════════════════════════════════════════════════════════════
# RESETEAR CONTRASEÑA
# ══════════════════════════════════════════════════════════════
def reset_password(username: str, new_password: str, must_change: bool = True) -> dict:
    """Restablece la contraseña de un usuario."""
    conn = _get_admin_connection()
    search_base = _get_search_base()

    # 1. Obtenemos el DN del usuario
    conn.search(search_base, f"(sAMAccountName={username})", SUBTREE, attributes=['distinguishedName'])
    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Usuario '{username}' no encontrado en el AD."}

    user_dn = str(conn.entries[0].distinguishedName)
    
    # 2. Intentamos cambiar la contraseña vía LDAP (Requiere LDAPS puerto 636)
    encoded_pwd = f'"{new_password}"'.encode('utf-16-le')
    result = conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [encoded_pwd])]})

    if not result:
        error_desc = conn.result.get('description', '')
        
        # Si el AD rechaza por unwillingToPerform (falta de LDAPS), usamos fallback nativo (ADSI / RPC)
        if 'unwillingToPerform' in error_desc or 'unwilling to perform' in error_desc.lower():
            import subprocess
            # Usamos PowerShell nativo con DirectoryEntry que utiliza RPC Seguro igual que la herramienta de Windows
            ps_script = f"""
$user = "{settings.SERVICE_USER}"
$pass = "{settings.SERVICE_PASS}"
$dn = "LDAP://{settings.LDAP_SERVER_IP}/$("{user_dn}")"
try {{
    $entry = New-Object System.DirectoryServices.DirectoryEntry($dn, $user, $pass)
    $entry.Invoke("SetPassword", "{new_password}")
    $entry.CommitChanges()
    Write-Output "SUCCESS"
}} catch {{
    Write-Output "ERROR: $_"
}}
"""
            ps_result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
            if "SUCCESS" not in ps_result.stdout:
                conn.unbind()
                return {"success": False, "error": f"Fallo en LDAP y en Fallback Nativo (RPC). Error nativo: {ps_result.stdout.strip()}"}
        else:
            conn.unbind()
            return {"success": False, "error": f"No se pudo cambiar la contraseña: {error_desc}. Asegúrate de que cumple la política de complejidad."}

    # Si must_change, forzar cambio en siguiente inicio de sesión (pwdLastSet = 0)
    if must_change:
        conn.modify(user_dn, {'pwdLastSet': [(MODIFY_REPLACE, ['0'])]})

    conn.unbind()
    return {"success": True, "message": f"Contraseña de '{username}' restablecida exitosamente."}


# ══════════════════════════════════════════════════════════════
# GESTIÓN DE GRUPOS AD (PowerShell)
# ══════════════════════════════════════════════════════════════

def get_ad_groups() -> list:
    """Obtiene la lista de grupos locales en el AD usando ldap3 (ya que RSAT/Get-ADGroup no está instalado localmente)."""
    conn = _get_admin_connection()
    search_base = _get_search_base()
    
    # Atributos de grupo
    attributes = ['cn', 'description', 'groupType', 'member', 'distinguishedName', 'objectGUID', 'isCriticalSystemObject']
    
    conn.search(search_base, "(objectClass=group)", SUBTREE, attributes=attributes)
    
    groups_list = []
    for entry in conn.entries:
        dn = str(entry.distinguishedName)
        
        # Ignorar grupos del sistema por defecto (Builtin o marcados como críticos)
        if "CN=Builtin" in dn:
            continue
        if hasattr(entry, 'isCriticalSystemObject') and entry.isCriticalSystemObject:
            if str(entry.isCriticalSystemObject.value).lower() == 'true':
                continue
                
        # Ignorar algunos grupos conocidos de sistema que a veces residen en Users
        cn_lower = str(entry.cn).lower()
        if cn_lower in ["domain computers", "domain controllers", "domain guests", "domain users", "enterprise read-only domain controllers", "group policy creator owners", "read-only domain controllers", "dnsadmins", "dnsupdateproxy", "ras and ias servers", "allowed rodc password replication group", "denied rodc password replication group", "cert publishers"]:
            continue

        # Extraer OU del DN
        dn_parts = dn.split(',')
        ou_parts = [p.replace('OU=', '').replace('DC=', '') for p in dn_parts if p.startswith('OU=') or p.startswith('DC=')]
        ou_path = "/".join(ou_parts) if ou_parts else "Users (Builtin)"
        
        # Determinar Scope y Type del groupType
        # Referencia groupType:
        # Security Global = -2147483646
        # Security Domain Local = -2147483644
        # Security Universal = -2147483640
        # Distribution = ... (positivos)
        gt = entry.groupType.value if entry.groupType else 0
        
        is_security = True if gt and gt < 0 else False
        
        scope = "Global"
        if gt in [-2147483644, 4]: scope = "DomainLocal"
        elif gt in [-2147483640, 8]: scope = "Universal"
        
        groups_list.append({
            "id": str(entry.objectGUID) if entry.objectGUID else "",
            "name": str(entry.cn),
            "scope": scope,
            "type": "Security" if is_security else "Distribution",
            "description": str(entry.description) if entry.description else "",
            "membersCount": len(entry.member) if entry.member else 0,
            "path": ou_path,
            "dn": dn
        })
        
    conn.unbind()
    return groups_list


def create_ad_group(data: dict) -> dict:
    """Crea un grupo nativo en el AD usando ldap3."""
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    scope = data.get("scope", "Global")
    category = data.get("type", "Security")
    path_dn = data.get("path", "").strip()

    if not name or not path_dn:
        return {"success": False, "error": "Faltan datos obligatorios (name, path)."}

    # Determinar groupType
    # Valores de groupType:
    # Security Global = -2147483646
    # Security DomainLocal = -2147483644
    # Security Universal = -2147483640
    # Distribution Global = 2
    # Distribution DomainLocal = 4
    # Distribution Universal = 8
    
    gt = 2 # Por defecto Global Distribution
    if category == "Security":
        if scope == "Global": gt = -2147483646
        elif scope == "DomainLocal": gt = -2147483644
        elif scope == "Universal": gt = -2147483640
    else:
        if scope == "Global": gt = 2
        elif scope == "DomainLocal": gt = 4
        elif scope == "Universal": gt = 8

    # Construir el DN del nuevo grupo
    group_dn = f"CN={name},{path_dn}"
    
    conn = _get_admin_connection()
    attributes = {
        'sAMAccountName': name,
        'groupType': gt,
        'description': description
    }
    
    if conn.add(group_dn, ['top', 'group'], attributes):
        conn.unbind()
        return {"success": True, "message": f"Grupo '{name}' creado correctamente en la OU."}
    else:
        error_msg = conn.result.get('description', '')
        conn.unbind()
        return {"success": False, "error": f"Error al crear grupo: {error_msg}"}


# ══════════════════════════════════════════════════════════════
# OPCIONES DE CUENTA (userAccountControl bits + pwdLastSet)
# ══════════════════════════════════════════════════════════════
# Bits de userAccountControl relevantes
UAC_BITS = {
    "must_change_password":        None,         # Se controla con pwdLastSet == 0
    "cannot_change_password":      0x0040,       # No se puede cambiar con LDAP estándar — solo lectura
    "password_never_expires":      0x10000,
    "store_reversible_encryption": 0x0080,
    "account_disabled":            0x0002,
    "account_locked":              0x0010,
    "smart_card_required":         0x40000,
    "trusted_for_delegation":      0x80000,
}

def get_account_options(username: str) -> dict:
    """Retorna las opciones de cuenta del usuario (flags UAC + pwdLastSet)."""
    conn = _get_admin_connection()
    search_base = _get_search_base()
    conn.search(search_base, f"(sAMAccountName={username})", SUBTREE,
                attributes=['distinguishedName', 'userAccountControl', 'pwdLastSet', 'accountExpires', 'lockoutTime'])

    if not conn.entries:
        conn.unbind()
        return {}

    entry = conn.entries[0]
    uac = int(str(entry.userAccountControl)) if 'userAccountControl' in entry else 0
    try:
        lockout_time_str = str(entry.lockoutTime) if 'lockoutTime' in entry and entry.lockoutTime else "0"
        if "-" in lockout_time_str:
            lockout_time = 0 if "1601" in lockout_time_str else 1
        else:
            lockout_time = int(lockout_time_str)
    except ValueError:
        lockout_time = 0
    
    # pwdLastSet is 0 if user must change password
    pwd_last_set = -1
    if 'pwdLastSet' in entry and entry.pwdLastSet.raw_values:
        try:
            pwd_last_set = int(entry.pwdLastSet.raw_values[0].decode('utf-8'))
        except:
            pass

    account_expires_raw = 0
    if 'accountExpires' in entry and entry.accountExpires.raw_values:
        try:
            account_expires_raw = int(entry.accountExpires.raw_values[0].decode('utf-8'))
        except:
            pass
            
    account_expires_never = account_expires_raw in (0, 9223372036854775807)
    account_expires_date = None
    if not account_expires_never:
        import datetime
        try:
            unix_time = (account_expires_raw / 10000000) - 11644473600
            account_expires_date = datetime.datetime.fromtimestamp(unix_time).strftime("%Y-%m-%d")
        except:
            account_expires_never = True

    options = {
        "must_change_password":        pwd_last_set == 0,
        "cannot_change_password":      bool(uac & 0x0040),
        "password_never_expires":      bool(uac & 0x10000),
        "store_reversible_encryption": bool(uac & 0x0080),
        "account_disabled":            bool(uac & 0x0002),
        "account_locked":              bool(lockout_time >= 1),
        "smart_card_required":         bool(uac & 0x40000),
        "trusted_for_delegation":      bool(uac & 0x80000),
        "account_expires_never":       account_expires_never,
        "account_expires_date":        account_expires_date,
        "raw_uac":                     uac,
        "dn":                          str(entry.distinguishedName),
    }
    conn.unbind()
    return options


def update_account_options(username: str, options: dict) -> dict:
    """
    Actualiza los flags UAC del usuario.
    options es un dict con los keys de UAC_BITS mapeados a bool.
    """
    conn = _get_admin_connection()
    search_base = _get_search_base()
    conn.search(search_base, f"(sAMAccountName={username})", SUBTREE,
                attributes=['distinguishedName', 'userAccountControl'])

    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Usuario '{username}' no encontrado."}

    entry = conn.entries[0]
    user_dn = str(entry.distinguishedName)
    uac = int(str(entry.userAccountControl)) if entry.userAccountControl else 512

    errors = []

    # Aplicar cada bit
    for key, bit in UAC_BITS.items():
        if key == "must_change_password" or bit is None or key == "account_locked":
            continue  # Se maneja por separado con pwdLastSet o lockoutTime
        if key in options:
            if options[key]:
                uac |= bit   # Encender el bit
            else:
                uac &= ~bit  # Apagar el bit

    result = conn.modify(user_dn, {'userAccountControl': [(MODIFY_REPLACE, [str(uac)])]})
    if not result:
        errors.append(f"Error actualizando UAC: {conn.result.get('description', 'desconocido')}")

    # must_change_password se controla con pwdLastSet
    if "must_change_password" in options:
        pwd_val = '0' if options["must_change_password"] else '-1'
        conn.modify(user_dn, {'pwdLastSet': [(MODIFY_REPLACE, [pwd_val])]})

    # account_locked se controla con lockoutTime (solo se permite desbloquear = 0)
    if "account_locked" in options and options["account_locked"] is False:
        conn.modify(user_dn, {'lockoutTime': [(MODIFY_REPLACE, ['0'])]})

    conn.unbind()
    if errors:
        return {"success": False, "error": "; ".join(errors)}
    return {"success": True, "message": "Opciones de cuenta actualizadas correctamente."}


# ══════════════════════════════════════════════════════════════
# EDITOR DE ATRIBUTOS COMPLETO
# ══════════════════════════════════════════════════════════════
# Lista de atributos LDAP a mostrar (equivalente al "Editor de atributos" de AD)
ALL_ATTRS = [
    'sAMAccountName', 'displayName', 'cn', 'givenName', 'sn', 'initials',
    'mail', 'proxyAddresses', 'mailNickname',
    'title', 'department', 'company', 'manager', 'employeeID', 'employeeType',
    'physicalDeliveryOfficeName', 'streetAddress', 'l', 'st', 'postalCode', 'co',
    'telephoneNumber', 'mobile', 'facsimileTelephoneNumber', 'ipPhone', 'homePhone',
    'wWWHomePage', 'url',
    'description', 'info', 'comment',
    'userPrincipalName', 'sAMAccountType', 'objectGUID',
    'userAccountControl', 'pwdLastSet', 'lastLogon', 'lastLogonTimestamp',
    'badPwdCount', 'badPasswordTime', 'lockoutTime',
    'whenCreated', 'whenChanged', 'accountExpires',
    'profilePath', 'scriptPath', 'homeDirectory', 'homeDrive',
    'distinguishedName', 'objectSid', 'primaryGroupID',
    'logonCount', 'logonHours',
    'memberOf',
]

def get_all_attributes(username: str) -> list:
    """Retorna todos los atributos AD del usuario según el esquema."""
    conn = _get_admin_connection()
    search_base = _get_search_base()
    
    # 1. Obtener todos los posibles atributos desde el esquema de AD
    schema_attrs = set()
    try:
        # El objeto user en AD hereda de top, person, organizationalPerson, user
        for c in ['top', 'person', 'organizationalPerson', 'user']:
            if c in conn.server.schema.object_classes:
                oc = conn.server.schema.object_classes[c]
                schema_attrs.update(oc.must_contain)
                schema_attrs.update(oc.may_contain)
        schema_attrs = sorted(list(schema_attrs), key=lambda x: x.lower())
    except Exception:
        schema_attrs = []
        
    # Fallback si por alguna razón falla la lectura del esquema
    if not schema_attrs:
        schema_attrs = sorted(ALL_ATTRS, key=lambda x: x.lower())
        
    # 2. Consultar al usuario pidiendo TODOS los atributos poblados ('*')
    conn.search(search_base, f"(sAMAccountName={username})", SUBTREE, attributes=['*'])

    if not conn.entries:
        conn.unbind()
        return []

    entry = conn.entries[0]

    # Atributos nativos de sistema / solo lectura (no se deben editar directamente)
    readonly_attrs = {
        'objectGUID', 'objectSid', 'distinguishedName', 'whenCreated',
        'whenChanged', 'sAMAccountType', 'primaryGroupID', 'memberOf',
        'lastLogon', 'lastLogonTimestamp', 'badPasswordTime', 'lockoutTime',
        'logonCount', 'logonHours', 'uSNCreated', 'uSNChanged', 'msDS-User-Account-Control-Computed',
        'dSCorePropagationData', 'msDS-SupportedEncryptionTypes', 'pwdLastSet', 'userAccountControl'
    }

    result = []
    
    # 3. Mapear cada atributo del esquema contra el valor real del usuario
    for attr_name in schema_attrs:
        try:
            if attr_name not in entry:
                value = "<no establecido>"
            else:
                attr_val = entry[attr_name]
                raw = attr_val.value
                if raw is None:
                    value = "<no establecido>"
                elif isinstance(raw, list):
                    value = "; ".join(str(v) for v in raw) if raw else "<no establecido>"
                elif hasattr(raw, 'strftime'):
                    value = raw.strftime("%d/%m/%Y %H:%M:%S")
                else:
                    value = str(raw)
        except Exception:
            value = "<no establecido>"

        is_readonly = attr_name in readonly_attrs
        is_editable = (not is_readonly) and (value != "<no establecido>") or (not is_readonly)

        result.append({
            "name": attr_name,
            "value": value,
            "editable": is_editable,
            "readonly": is_readonly,
        })

    conn.unbind()
    return result


def update_attribute(username: str, attr_name: str, new_value: str) -> dict:
    """Actualiza un atributo LDAP específico del usuario."""
    readonly_attrs = {
        'objectGUID', 'objectSid', 'distinguishedName', 'whenCreated',
        'whenChanged', 'sAMAccountType', 'primaryGroupID', 'memberOf',
        'lastLogon', 'lastLogonTimestamp', 'badPasswordTime', 'lockoutTime',
    }

    if attr_name in readonly_attrs:
        return {"success": False, "error": f"El atributo '{attr_name}' es de solo lectura."}

    conn = _get_admin_connection()
    search_base = _get_search_base()
    conn.search(search_base, f"(sAMAccountName={username})", SUBTREE, attributes=['distinguishedName'])

    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Usuario '{username}' no encontrado."}

    user_dn = str(conn.entries[0].distinguishedName)
    value_to_set = [] if new_value.strip() == "" else [new_value.strip()]
    result = conn.modify(user_dn, {attr_name: [(MODIFY_REPLACE, value_to_set)]})

    if result:
        conn.unbind()
        return {"success": True, "message": f"Atributo '{attr_name}' actualizado correctamente."}
    else:
        error = conn.result.get('description', 'Error desconocido')
        conn.unbind()
        return {"success": False, "error": f"Error actualizando '{attr_name}': {error}"}


def update_attributes_bulk(username: str, updates: dict) -> dict:
    """Actualiza múltiples atributos LDAP de un usuario en una sola operación."""
    readonly_attrs = {
        'objectGUID', 'objectSid', 'distinguishedName', 'whenCreated',
        'whenChanged', 'sAMAccountType', 'primaryGroupID', 'memberOf',
        'lastLogon', 'lastLogonTimestamp', 'badPasswordTime', 'lockoutTime',
    }

    changes = {}
    for attr_name, new_value in updates.items():
        if attr_name in readonly_attrs:
            continue
        
        # Si el valor está vacío, se limpia el atributo, si no, se actualiza
        if new_value is None:
            value_to_set = []
        elif isinstance(new_value, str) and new_value.strip() == "":
            value_to_set = []
        else:
            if isinstance(new_value, list):
                value_to_set = [v.strip() if isinstance(v, str) else v for v in new_value]
            else:
                value_to_set = [new_value.strip() if isinstance(new_value, str) else new_value]
            
        changes[attr_name] = [(MODIFY_REPLACE, value_to_set)]

    if not changes:
        return {"success": True, "message": "No hay atributos válidos para actualizar."}

    conn = _get_admin_connection()
    search_base = _get_search_base()
    conn.search(search_base, f"(sAMAccountName={username})", SUBTREE, attributes=['distinguishedName'])

    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Usuario '{username}' no encontrado."}

    user_dn = str(conn.entries[0].distinguishedName)
    result = conn.modify(user_dn, changes)

    if result:
        conn.unbind()
        return {"success": True, "message": "Atributos actualizados correctamente."}
    else:
        error = conn.result.get('description', 'Error desconocido')
        conn.unbind()
        return {"success": False, "error": f"Error actualizando atributos: {error}"}


# ══════════════════════════════════════════════════════════════
# GESTIÓN DE GRUPOS (Miembro de)
# ══════════════════════════════════════════════════════════════
def search_ad_objects(query: str, limit: int = 15) -> list:
    """Busca usuarios y grupos simultáneamente en el AD (Typeahead)."""
    conn = _get_admin_connection()
    search_base = _get_search_base()

    safe_query = query.replace("(", "").replace(")", "").replace("*", "").replace("\\", "").strip()
    if not safe_query:
        conn.unbind()
        return []

    search_filter = (
        f"(&(|(objectClass=user)(objectClass=group))"
        f"(|(sAMAccountName=*{safe_query}*)(name=*{safe_query}*)(displayName=*{safe_query}*)))"
    )

    entries = _paged_search(
        conn=conn,
        search_base=search_base,
        search_filter=search_filter,
        attributes=['sAMAccountName', 'name', 'displayName', 'objectClass', 'userPrincipalName'],
        limit=limit
    )

    results = []
    for entry in entries:
        classes = [c.lower() for c in entry.objectClass.values] if 'objectClass' in entry else []
        is_group = 'group' in classes
        obj_type = "Group" if is_group else "User"
        
        display_name = str(entry.displayName) if 'displayName' in entry and entry.displayName else str(entry.name) if 'name' in entry else ""
        sam = str(entry.sAMAccountName) if 'sAMAccountName' in entry else ""
        upn = str(entry.userPrincipalName) if 'userPrincipalName' in entry and entry.userPrincipalName else sam

        results.append({
            "name": display_name,
            "sAMAccountName": sam,
            "upn": upn,
            "type": obj_type
        })
    
    conn.unbind()
    results.sort(key=lambda x: x['name'])
    return results

def search_ad_groups(query: str, limit: int = 20) -> list:
    """Busca grupos de seguridad en el AD por nombre, sAMAccountName o descripción."""
    conn = _get_admin_connection()
    search_base = _get_search_base()
    safe_query = query.replace("(", "").replace(")", "").replace("\\", "").strip()
    if not safe_query:
        conn.unbind()
        return []
    # Buscar en cn, sAMAccountName y description
    search_filter = (
        f"(&(objectCategory=group)"
        f"(|(cn=*{safe_query}*)(sAMAccountName=*{safe_query}*)(description=*{safe_query}*)))"
    )
    try:
        conn.search(search_base, search_filter, SUBTREE,
                    attributes=['cn', 'distinguishedName', 'description', 'groupType', 'sAMAccountName'],
                    size_limit=limit)
    except Exception as e:
        print(f"❌ [AD] Error buscando grupos: {e}")
        conn.unbind()
        return []
    results = []
    for entry in conn.entries:
        # Determinar tipo de grupo
        group_type_val = int(str(entry.groupType)) if entry.groupType else 0
        if group_type_val & 0x80000000:
            g_type = "Seguridad"
        else:
            g_type = "Distribución"
        results.append({
            "name": str(entry.cn),
            "dn": str(entry.distinguishedName),
            "description": str(entry.description) if entry.description else "",
            "type": g_type,
        })
    conn.unbind()
    results.sort(key=lambda x: x['name'])
    return results

def get_ad_group_members(group_name: str) -> list:
    """Obtiene los miembros de un grupo (usuarios y/o subgrupos)."""
    conn = _get_admin_connection()
    search_base = _get_search_base()
    conn.search(search_base, f"(sAMAccountName={group_name})", SUBTREE, attributes=['member'])
    if not conn.entries:
        conn.unbind()
        return []
    
    group_entry = conn.entries[0]
    members = []
    
    if 'member' in group_entry and group_entry.member:
        member_dns = group_entry.member
        for member_dn in member_dns:
            # Buscar cada miembro para obtener su sAMAccountName, ObjectClass y DisplayName
            conn.search(str(member_dn), "(objectClass=*)", attributes=['sAMAccountName', 'displayName', 'objectClass'])
            if conn.entries:
                entry = conn.entries[0]
                classes = [c.lower() for c in entry.objectClass.values] if 'objectClass' in entry else []
                m_type = 'Group' if 'group' in classes else 'User'
                
                members.append({
                    "name": str(entry.displayName) if 'displayName' in entry and entry.displayName else str(entry.sAMAccountName) if 'sAMAccountName' in entry else str(member_dn),
                    "sAMAccountName": str(entry.sAMAccountName) if 'sAMAccountName' in entry else "",
                    "type": m_type,
                    "dn": str(member_dn)
                })
    conn.unbind()
    members.sort(key=lambda x: x['name'])
    return members

def add_ad_group_member(group_name: str, member_name: str) -> dict:
    """Agrega un miembro (usuario o grupo) a un grupo del AD."""
    from ldap3 import MODIFY_ADD
    conn = _get_admin_connection()
    search_base = _get_search_base()
    
    # 1. Buscar el grupo
    conn.search(search_base, f"(sAMAccountName={group_name})", SUBTREE, attributes=['distinguishedName'])
    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Grupo '{group_name}' no encontrado."}
    group_dn = str(conn.entries[0].distinguishedName)
    
    # 2. Buscar el miembro
    conn.search(search_base, f"(sAMAccountName={member_name})", SUBTREE, attributes=['distinguishedName'])
    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Miembro '{member_name}' no encontrado."}
    member_dn = str(conn.entries[0].distinguishedName)
    
    # 3. Agregar
    result = conn.modify(group_dn, {'member': [(MODIFY_ADD, [member_dn])]})
    if result:
        conn.unbind()
        return {"success": True, "message": "Miembro agregado al grupo correctamente."}
    else:
        error = conn.result.get('description', 'Error desconocido')
        conn.unbind()
        return {"success": False, "error": f"Error agregando al grupo: {error}"}

def remove_ad_group_member(group_name: str, member_name: str) -> dict:
    """Quita un miembro (usuario o grupo) de un grupo del AD."""
    from ldap3 import MODIFY_DELETE
    conn = _get_admin_connection()
    search_base = _get_search_base()
    
    # 1. Buscar el grupo
    conn.search(search_base, f"(sAMAccountName={group_name})", SUBTREE, attributes=['distinguishedName'])
    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Grupo '{group_name}' no encontrado."}
    group_dn = str(conn.entries[0].distinguishedName)
    
    # 2. Buscar el miembro
    conn.search(search_base, f"(sAMAccountName={member_name})", SUBTREE, attributes=['distinguishedName'])
    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Miembro '{member_name}' no encontrado."}
    member_dn = str(conn.entries[0].distinguishedName)
    
    # 3. Remover
    result = conn.modify(group_dn, {'member': [(MODIFY_DELETE, [member_dn])]})
    if result:
        conn.unbind()
        return {"success": True, "message": "Miembro removido del grupo correctamente."}
    else:
        error = conn.result.get('description', 'Error desconocido')
        conn.unbind()
        return {"success": False, "error": f"Error removiendo del grupo: {error}"}


def add_user_to_group(username: str, group_dn: str) -> dict:
    """Agrega un usuario a un grupo del AD."""
    from ldap3 import MODIFY_ADD
    conn = _get_admin_connection()
    search_base = _get_search_base()
    conn.search(search_base, f"(sAMAccountName={username})", SUBTREE, attributes=['distinguishedName'])
    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Usuario '{username}' no encontrado."}
    user_dn = str(conn.entries[0].distinguishedName)
    result = conn.modify(group_dn, {'member': [(MODIFY_ADD, [user_dn])]})
    if result:
        conn.unbind()
        return {"success": True, "message": "Usuario agregado al grupo correctamente."}
    else:
        error = conn.result.get('description', 'Error desconocido')
        conn.unbind()
        return {"success": False, "error": f"Error agregando al grupo: {error}"}


def remove_user_from_group(username: str, group_dn: str) -> dict:
    """Quita un usuario de un grupo del AD."""
    from ldap3 import MODIFY_DELETE
    conn = _get_admin_connection()
    search_base = _get_search_base()
    conn.search(search_base, f"(sAMAccountName={username})", SUBTREE, attributes=['distinguishedName'])
    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": f"Usuario '{username}' no encontrado."}
    user_dn = str(conn.entries[0].distinguishedName)
    result = conn.modify(group_dn, {'member': [(MODIFY_DELETE, [user_dn])]})
    if result:
        conn.unbind()
        return {"success": True, "message": "Usuario removido del grupo correctamente."}
    else:
        error = conn.result.get('description', 'Error desconocido')
        conn.unbind()
        return {"success": False, "error": f"Error removiendo del grupo: {error}"}


# ══════════════════════════════════════════════════════════════
# CARPETAS ASIGNADAS (Grupos con acceso a recursos compartidos)
# ══════════════════════════════════════════════════════════════
def get_folder_groups(username: str) -> list:
    """
    Retorna los grupos de seguridad del usuario que probablemente
    otorgan acceso a carpetas o recursos de red.
    Busca grupos que contengan prefijos comunes de carpetas: GG_, FS_, NTFS_, RES_, etc.
    """
    conn = _get_admin_connection()
    search_base = _get_search_base()
    conn.search(search_base, f"(sAMAccountName={username})", SUBTREE, attributes=['memberOf'])

    if not conn.entries:
        conn.unbind()
        return []

    entry = conn.entries[0]
    folder_prefixes = ('GG_', 'FS_', 'NTFS_', 'RES_', 'SHARE_', 'ACL_', 'DFS_', 'FILE_', 'FOLDER_')

    groups = []
    if entry.memberOf:
        for group_dn in entry.memberOf:
            group_name = str(group_dn).split(",")[0].replace("CN=", "")
            upper_name = group_name.upper()

            if any(upper_name.startswith(p) for p in folder_prefixes):
                # Intentar extraer la ruta del nombre del grupo
                groups.append({
                    "name": group_name,
                    "dn": str(group_dn),
                    "type": "Recurso compartido",
                })

    conn.unbind()
    return groups


# ══════════════════════════════════════════════════════════════
# CREACIÓN DE USUARIOS
# ══════════════════════════════════════════════════════════════
def get_organizational_units() -> list:
    """Retorna todas las OUs y el contenedor Users."""
    conn = _get_admin_connection()
    search_base = _get_search_base()
    ous = []
    
    # 1. OUs
    conn.search(search_base, "(objectClass=organizationalUnit)", SUBTREE, attributes=['distinguishedName', 'ou'])
    for entry in conn.entries:
        ous.append({
            "name": str(entry.ou) if entry.ou else str(entry.distinguishedName).split(",")[0].replace("OU=", ""),
            "dn": str(entry.distinguishedName),
            "type": "OU"
        })
        
    # 2. Contenedor por defecto Users
    conn.search(search_base, "(&(objectClass=container)(cn=Users))", SUBTREE, attributes=['distinguishedName', 'cn'])
    for entry in conn.entries:
        ous.append({
            "name": str(entry.cn) if entry.cn else "Users",
            "dn": str(entry.distinguishedName),
            "type": "Container"
        })
        
    conn.unbind()
    ous.sort(key=lambda x: x['dn'])
    return ous


def create_ad_user(data: dict) -> dict:
    """Crea un usuario nativo en el AD."""
    conn = _get_admin_connection()
    user_dn = f"CN={data['fullName']},{data['ou']}"
    
    attributes = {
        'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
        'sAMAccountName': data['samAccountName'],
        'userPrincipalName': data['upn'],
        'givenName': data['firstName'],
        'sn': data['lastName'],
        'displayName': data['fullName'],
        'description': data.get('description', 'Creado desde IT Admin Platform'),
        'mail': data['upn'],
    }
    
    if data.get('initials'):
        attributes['initials'] = data['initials']
    if data.get('jobTitle'):
        attributes['title'] = data['jobTitle']
    if data.get('department'):
        attributes['department'] = data['department']
    if data.get('managerDn'):
        attributes['manager'] = data['managerDn']
    if data.get('telephoneNumber'):
        attributes['telephoneNumber'] = data['telephoneNumber']
        attributes['ipPhone'] = data['telephoneNumber']
        
    # Validar si el dominio es el de la nube para inyectar proxyAddresses
    if data['upn'].lower().endswith('@105code.cloud'):
        attributes['proxyAddresses'] = [f"SMTP:{data['upn']}"]
        
    # 1. Crear el objeto usuario
    result = conn.add(user_dn, attributes=attributes)
    if not result:
        error = conn.result.get('description', 'Error desconocido al crear usuario.')
        conn.unbind()
        return {"success": False, "error": error}
        
    # 2. Establecer la contraseña (requerido antes de habilitar la cuenta)
    pwd_bytes = f'"{data["password"]}"'.encode('utf-16-le')
    result_pwd = conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [pwd_bytes])]})
    
    if not result_pwd:
        error_desc = conn.result.get('description', '')
        if 'unwillingToPerform' in error_desc or 'unwilling to perform' in error_desc.lower():
            import subprocess
            ps_script = f"""
$user = "{settings.SERVICE_USER}"
$pass = "{settings.SERVICE_PASS}"
$dn = "LDAP://{settings.LDAP_SERVER_IP}/$("{user_dn}")"
try {{
    $entry = New-Object System.DirectoryServices.DirectoryEntry($dn, $user, $pass)
    $entry.Invoke("SetPassword", "{data['password']}")
    $entry.CommitChanges()
    Write-Output "SUCCESS"
}} catch {{
    Write-Output "ERROR: $_"
}}
"""
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
    
    # 3. Configurar flags (UAC y pwdLastSet)
    uac = 512 # NORMAL_ACCOUNT (512 = cuenta habilitada por defecto)
    if data.get('accountDisabled'):
        uac |= 0x0002
    if data.get('cannotChangePassword'):
        uac |= 0x0040
    if data.get('passwordNeverExpires'):
        uac |= 0x10000
        
    modifications = {'userAccountControl': [(MODIFY_REPLACE, [str(uac)])]}
    if data.get('mustChangePassword'):
        modifications['pwdLastSet'] = [(MODIFY_REPLACE, ['0'])]
    else:
        modifications['pwdLastSet'] = [(MODIFY_REPLACE, ['-1'])]
        
    result_uac = conn.modify(user_dn, modifications)
    
    conn.unbind()
    
    return {"success": True, "message": f"Usuario {data['samAccountName']} creado correctamente."}

def unlock_ad_account(username: str) -> dict:
    import subprocess
    import json
    ps_script = f"""
$user = "{settings.SERVICE_USER}"
$pass = "{settings.SERVICE_PASS}"
$secpass = ConvertTo-SecureString $pass -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential ($user, $secpass)
try {{
    Unlock-ADAccount -Identity "{username}" -Server "{settings.LDAP_SERVER_IP}" -Credential $cred
    Write-Output '{{"success": true}}'
}} catch {{
    Write-Output '{{"success": false, "error": "' + $_.Exception.Message + '"}}'
}}
"""
    result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
    try:
        # Extraemos JSON válido de la salida
        for line in result.stdout.strip().split('\\n'):
            if line.startswith('{'):
                return json.loads(line)
        return {"success": False, "error": "No se pudo parsear el resultado de PowerShell"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def reset_ad_password(username: str) -> dict:
    import subprocess
    import json
    import random
    import string
    
    # Generar contraseña temporal segura
    chars = string.ascii_letters + string.digits + "!@#$%&*"
    temp_pwd = ''.join(random.choice(chars) for _ in range(12))
    
    ps_script = f"""
$user = "{settings.SERVICE_USER}"
$pass = "{settings.SERVICE_PASS}"
$secpass = ConvertTo-SecureString $pass -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential ($user, $secpass)
$tempSecPass = ConvertTo-SecureString "{temp_pwd}" -AsPlainText -Force

try {{
    Set-ADAccountPassword -Identity "{username}" -NewPassword $tempSecPass -Server "{settings.LDAP_SERVER_IP}" -Credential $cred -Reset:$true
    Set-ADUser -Identity "{username}" -ChangePasswordAtLogon $true -Server "{settings.LDAP_SERVER_IP}" -Credential $cred
    Write-Output '{{"success": true, "temp_password": "{temp_pwd}"}}'
}} catch {{
    Write-Output '{{"success": false, "error": "' + $_.Exception.Message + '"}}'
}}
"""
    result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
    try:
        for line in result.stdout.strip().split('\\n'):
            if line.startswith('{'):
                return json.loads(line)
        return {"success": False, "error": "No se pudo parsear el resultado de PowerShell", "stderr": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def manage_proxy_address(username: str, alias: str, action: str) -> dict:
    """Añade o elimina un proxyAddress (alias) y fuerza la sincronización delta."""
    conn = _get_admin_connection()
    search_base = _get_search_base()
    conn.search(search_base, f"(sAMAccountName={username})", attributes=['distinguishedName', 'proxyAddresses'])
    
    if not conn.entries:
        conn.unbind()
        return {"success": False, "error": "Usuario no encontrado"}
        
    entry = conn.entries[0]
    user_dn = str(entry.distinguishedName)
    current_proxies = [str(a) for a in entry.proxyAddresses] if entry.proxyAddresses else []
    
    from ldap3 import MODIFY_ADD, MODIFY_DELETE
    modify_op = MODIFY_ADD if action == 'add' else MODIFY_DELETE
    
    if action == 'add':
        full_alias = alias if ':' in alias else f"smtp:{alias}"
    else:
        full_alias = alias
    
    if action == 'add' and full_alias in current_proxies:
        conn.unbind()
        return {"success": False, "error": "El alias ya existe"}
        
    if action == 'remove' and full_alias not in current_proxies:
        conn.unbind()
        return {"success": False, "error": "El alias no se encontró en la lista"}
    
    result = conn.modify(user_dn, {'proxyAddresses': [(modify_op, [full_alias])]})
    conn.unbind()
    
    if not result:
        return {"success": False, "error": "Fallo al modificar LDAP"}
        
    # Forzar ciclo delta de Entra Connect localmente
    import subprocess
    ps_script = 'Start-ADSyncSyncCycle -PolicyType Delta'
    subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
    
    return {"success": True, "message": f"Alias {'agregado' if action == 'add' else 'eliminado'} correctamente."}

def get_all_gpos():
    """Obtiene todas las directivas de grupo (GPOs) desde Active Directory mediante LDAP."""
    conn = _get_admin_connection()
    search_base = "CN=Policies,CN=System," + _get_search_base()
    search_filter = "(objectClass=groupPolicyContainer)"
    attributes = ["displayName", "cn", "whenChanged", "flags", "gPCMachineExtensionNames", "gPCUserExtensionNames"]
    
    try:
        entries = _paged_search(conn, search_base, search_filter, attributes)
        gpos = []
        for entry in entries:
            attrs = entry.entry_attributes_as_dict
            
            # Determinar tipo
            has_machine = bool(attrs.get("gPCMachineExtensionNames"))
            has_user = bool(attrs.get("gPCUserExtensionNames"))
            if has_machine and has_user:
                gpo_type = "Equipo y Usuario"
            elif has_machine:
                gpo_type = "Equipo"
            elif has_user:
                gpo_type = "Usuario"
            else:
                gpo_type = "Vacía/Desconocido"
                
            # Determinar estado
            flags = attrs.get("flags", [0])[0]
            # 0 = Enabled, 1 = User disabled, 2 = Machine disabled, 3 = All disabled
            if flags == 3:
                status = "Inactivo"
            else:
                status = "Activo"
                
            gpos.append({
                "id": attrs.get("cn", [""])[0],
                "name": attrs.get("displayName", ["Sin Nombre"])[0],
                "type": gpo_type,
                "target": "Varias OUs", # Nota: El alcance real requiere parsear gPLink en las OUs
                "status": status,
                "last_modified": _parse_ad_timestamp(attrs.get("whenChanged", [None])[0])
            })
        return gpos
    except Exception as e:
        print(f"Error getting GPOs: {e}")
        return []
    finally:
        conn.unbind()
