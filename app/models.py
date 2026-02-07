from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, JSON
from app.database import Base
from datetime import datetime
from sqlalchemy.sql import func

class Brand(Base):
    __tablename__ = "brands"

    id=Column(Integer, primary_key=True, index=True)
    name=Column(String(255), nullable=False)
    email=Column(String(255), nullable=False, unique=True)
    website=Column(String(255))
    instagram=Column(String(255))
    category=Column(String(100))
    notes=Column(Text)
    status=Column(String(50), default='not_contacted')
    discovered_by_ai=Column(Boolean, default=False)
    discovered_at=Column(TIMESTAMP)
    brand_metadata=Column(JSON)
    last_pitched_at=Column(TIMESTAMP)
    created_at=Column(TIMESTAMP, server_default=func.now())
    updated_at=Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
