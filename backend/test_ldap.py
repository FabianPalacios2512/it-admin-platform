from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPBindError, LDAPException

LDAP_SERVER_IP = '192.168.20.100'

def test_bind(username, password):
    print(f"Probando autenticación para: {username}")
    try:
        server = Server(LDAP_SERVER_IP, get_info=ALL)
        conn = Connection(server, user=username, password=password, auto_bind=True)
        print(f"✅ Autenticación exitosa para {username}")
        print(f"Información del servidor LDAP: {server.info}")
        conn.unbind()
    except LDAPBindError as e:
        print(f"❌ Credenciales inválidas para {username}: {e}")
    except LDAPException as e:
        print(f"❌ Error de conexión LDAP: {e}")
    except Exception as e:
        print(f"❌ Otro error: {e}")

if __name__ == '__main__':
    password = 'Colombia12345++'
    username = 'fapaternina'
    
    print("--- PRUEBA 1: Solo usuario ---")
    test_bind(username, password)
    
    print("\n--- PRUEBA 2: Con Dominio Corto (NetBIOS) ---")
    # REEMPLAZA 'TUDOMINIO' POR TU DOMINIO REAL (ej: 'HOGARYMODA' o 'HYM')
    test_bind(f"TUDOMINIO\\{username}", password)
    
    print("\n--- PRUEBA 3: Con Dominio Largo (UPN) ---")
    # REEMPLAZA 'tudominio.local' POR TU DOMINIO REAL (ej: 'hogarymoda.local' o 'hogarymoda.com.co')
    test_bind(f"{username}@code.local", password)
