import os
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import settings

# Engine and Session Setup
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI Dependency for database session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    caller_phone = Column(String(30), nullable=True)
    caller_name = Column(String(100), nullable=True)
    budget_lakh = Column(Float, nullable=True)
    location_pref = Column(String(100), nullable=True)
    property_type = Column(String(50), nullable=True)
    transaction_type = Column(String(20), nullable=True)
    timeline = Column(String(50), nullable=True)
    lead_score = Column(Integer, default=0)
    status = Column(String(30), default="new")  # new / qualified / escalated / booked
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    calls = relationship("Call", back_populates="lead")


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    total_turns = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    models_used = Column(Text, default="[]")  # JSON string of model names
    recording_url = Column(String(255), nullable=True)
    outcome = Column(String(30), default="incomplete")  # qualified / escalated / incomplete

    lead = relationship("Lead", back_populates="calls")


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    turn_number = Column(Integer, default=1)
    user_text = Column(Text, nullable=False)
    detected_language = Column(String(20), nullable=True)
    detected_intent = Column(String(50), nullable=True)
    complexity = Column(String(20), nullable=True)
    model_used = Column(String(50), nullable=True)
    response_text = Column(Text, nullable=False)
    latency_ms = Column(Float, default=0.0)
    cost_usd = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)


class SiteVisit(Base):
    __tablename__ = "site_visits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=False)
    property_id = Column(String(50), nullable=True)
    preferred_date = Column(String(50), nullable=False)
    preferred_time = Column(String(50), nullable=False)
    session_id = Column(String(100), nullable=True, index=True)
    status = Column(String(30), default="confirmed")
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Creates database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
