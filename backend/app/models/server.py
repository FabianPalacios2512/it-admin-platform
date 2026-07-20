from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base


class ServerConfig(Base):
    __tablename__ = "server_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)                    # Ej: "DC-CODE-01"
    server_type = Column(String, nullable=False)             # "da", "ha", "files", "printers"
    ip = Column(String, nullable=False)                      # IP o hostname
    domain = Column(String, nullable=True)                   # Ej: "code.local" (solo para DA/HA)
    admin_user = Column(String, nullable=False)              # Ej: "code\\administrador"
    admin_pass = Column(String, nullable=False)              # Contraseña (encriptada con Fernet)
    allowed_groups = Column(String, nullable=True)           # Grupos permitidos para login, separados por coma
    is_primary = Column(Boolean, default=False)              # ¿Es el servidor principal para login?
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
