"""
Configuración central de la plataforma.
Soporta configuración dinámica desde la DB o fallback a valores hardcoded.
"""


from pydantic_settings import BaseSettings

class EnvSettings(BaseSettings):
    ENTRA_TENANT_ID: str = ""
    ENTRA_CLIENT_ID: str = ""
    ENTRA_CLIENT_SECRET: str = ""
    UNIFI_HOST: str = "192.168.1.111"
    UNIFI_PORT: int = 8443
    UNIFI_USER: str = "admin"
    UNIFI_PASS: str = "admin"
    UNIFI_SITE: str = "default"

    class Config:
        env_file = ".env"
        extra = "ignore"

env_settings = EnvSettings()

class Settings:
    """Valores por defecto (fallback si no hay servidores en la DB)."""
    AD_DOMAIN: str = "code.local"
    LDAP_SERVER_IP: str = "192.168.20.100"
    SERVICE_USER: str = r"code\administrador"
    SERVICE_PASS: str = "Colombia123456++"
    ALLOWED_GROUPS: list = ["SG_Admins_SoporteTI"]


settings = Settings()


def get_primary_server(server_type: str = "da"):
    """
    Busca el servidor primario del tipo indicado en la DB.
    Si no encuentra ninguno, lanza un error para obligar al usuario a configurarlo.
    Retorna un dict con: ip, domain, admin_user, admin_pass, allowed_groups.
    """
    try:
        from app.core.database import SessionLocal
        from app.models.server import ServerConfig
        from app.core.encryption import decrypt_password

        db = SessionLocal()
        server = db.query(ServerConfig).filter(
            ServerConfig.server_type == server_type,
            ServerConfig.is_primary == True
        ).first()

        if server:
            result = {
                "ip": server.ip,
                "domain": server.domain or "code.local",
                "admin_user": server.admin_user,
                "admin_pass": decrypt_password(server.admin_pass),
                "allowed_groups": [g.strip() for g in (server.allowed_groups or "").split(",") if g.strip()],
            }
            db.close()
            return result
        db.close()
    except Exception as e:
        print(f"⚠️ [Config] Error al leer servidores de la DB: {e}")

    # Ya NO hay fallback. Si no hay servidor en la DB, fallamos.
    raise ValueError(f"No hay ningún servidor de tipo '{server_type}' configurado como Primario. Por favor, agregue uno desde la configuración.")
