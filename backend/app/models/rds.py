from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from datetime import datetime
from app.core.database import Base

class RdsConfig(Base):
    __tablename__ = "rds_configs"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("server_configs.id"), nullable=False)
    cron_time = Column(String, nullable=True)             # "23:00"
    cron_days = Column(String, nullable=True)             # "0,1,2,3,4,5,6" (0=Mon, 6=Sun or whatever cron format we use)
    temp_path = Column(String, default="C:\\conteo")
    file_prefix = Column(String, default="nova.xl")
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
