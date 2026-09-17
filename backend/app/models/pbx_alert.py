from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class PBXAlert(Base):
    __tablename__ = "pbx_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, index=True)  # BREACH, BRUTE_FORCE, TOLL_FRAUD
    extension = Column(String, index=True)
    attacker_ip = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    details = Column(String, nullable=True)
    ai_summary = Column(String, nullable=True)
    resolved = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
