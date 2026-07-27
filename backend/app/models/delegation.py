from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from app.core.database import Base

class TemporaryDelegation(Base):
    __tablename__ = "temporary_delegations"

    id = Column(Integer, primary_key=True, index=True)
    source_upn = Column(String, index=True, nullable=False)
    target_upn = Column(String, index=True, nullable=False)
    permission_type = Column(String, nullable=False) # FullAccess, SendAs, SendOnBehalf
    expiration_date = Column(DateTime, nullable=True) # Null = no expire
    status = Column(String, default="Active") # Active, Revoked, Failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
