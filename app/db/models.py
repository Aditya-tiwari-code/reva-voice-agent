# SQLite Table Definitions (SQLAlchemy)

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    caller_phone = Column(String(20), index=True)
    name = Column(String(100), nullable=True)
    preferred_city = Column(String(50), nullable=True)
    budget_lakh = Column(Float, nullable=True)
    bhk_preference = Column(Integer, nullable=True)
    lead_score = Column(Float, default=0.0)
    qualification_status = Column(String(20), default="unqualified")  # Qualified / Warm / Cold
    created_at = Column(DateTime, default=datetime.utcnow)

class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String(50), unique=True, index=True)
    lead_id = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
