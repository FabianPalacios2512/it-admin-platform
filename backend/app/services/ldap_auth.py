from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPBindError, LDAPException
from app.core.config import settings, get_primary_server

def authenticate_ldap(username: str, password: str) -> dict:
    """
    Intenta autenticar a un usuario contra el Active Directory.
    Usa el servidor primario configurado en la DB (o fallback hardcoded).
    Retorna un diccionario con 'authenticated' (bool), 'display_name' y opcional 'error'.
    """
    try:
        try:
            cfg = get_primary_server("da")
        except ValueError as ve:
            return {"authenticated": False, "error": str(ve)}
            
        server = Server(cfg["ip"], get_info=ALL)
        domain = cfg["domain"]
        allowed_groups = cfg["allowed_groups"]

        # 1. AUTENTICACIÓN: Validar si la contraseña del usuario es correcta
        if not password or len(password.strip()) == 0:
            return {"authenticated": False, "error": "La contraseña no puede estar vacía."}
            
        upn = f"{username}@{domain}" if "@" not in username else username
        try:
            user_conn = Connection(server, user=upn, password=password, auto_bind=True)
            user_conn.unbind() # Clave correcta, cerramos su conexión
        except LDAPBindError:
            return {"authenticated": False, "error": "Credenciales inválidas."}

        # 2. AUTORIZACIÓN: Conectarse como Service Account para leer perfil y grupos
        admin_conn = Connection(server, user=cfg["admin_user"], password=cfg["admin_pass"], auto_bind=True)
        
        search_filter = f"(sAMAccountName={username})"
        search_base = f"DC={domain.replace('.', ',DC=')}"
        
        display_name = username
        is_authorized = False
        
        try:
            admin_conn.search(search_base=search_base,
                              search_filter=search_filter,
                              search_scope=SUBTREE,
                              attributes=['displayName', 'givenName', 'sn', 'memberOf'])
                              
            if admin_conn.entries:
                entry = admin_conn.entries[0]
                
                # Obtener el nombre para mostrar
                if 'displayName' in entry and entry.displayName:
                    display_name = str(entry.displayName)
                elif 'givenName' in entry and entry.givenName:
                    display_name = f"{entry.givenName} {entry.sn if 'sn' in entry else ''}".strip()
                
                # Validar grupos
                if not allowed_groups:
                    # Si no hay grupos configurados, cualquiera puede entrar
                    is_authorized = True
                elif 'memberOf' in entry:
                    user_groups = [str(group).split(',')[0].replace('CN=', '') for group in entry.memberOf]
                    print(f"🔒 [Auth] Grupos del usuario {username}: {user_groups}")
                    
                    if any(allowed in user_groups for allowed in allowed_groups):
                        is_authorized = True
                        
        except Exception as search_e:
            print(f"❌ [Auth] Error buscando atributos con Service Account: {search_e}")
            
        admin_conn.unbind()
        
        if not is_authorized:
            return {"authenticated": False, "error": f"Acceso denegado. No perteneces a los grupos permitidos: {allowed_groups}"}

        return {
            "authenticated": True,
            "display_name": display_name
        }

    except LDAPException as e:
        print(f"❌ [Auth] Error interno LDAP: {e}")
        return {"authenticated": False, "error": "Error de comunicación con el Directorio Activo."}
