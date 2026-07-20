from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    username = Column(String, index=True)
    action = Column(String)
    target = Column(String)
    status = Column(String)
    source = Column(String, default="Web")
    event_id = Column(String, nullable=True, unique=True)
