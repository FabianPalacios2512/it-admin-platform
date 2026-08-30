from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base

class LicenseAudit(Base):
    __tablename__ = "license_audits"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, index=True)
    user_principal_name = Column(String, index=True)
    display_name = Column(String)
    action = Column(String) # "NOTE" o "RECOVERED"
    note = Column(String, nullable=True)
    licenses = Column(String, nullable=True)
    saved_usd = Column(Integer, default=0)
