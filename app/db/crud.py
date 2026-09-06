# DB Read/Write Helper Functions

from sqlalchemy.orm import Session
from app.db.models import Lead, CallLog

def create_lead(db: Session, caller_phone: str, name: str = None) -> Lead:
    lead = Lead(caller_phone=caller_phone, name=name)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead

def get_lead_by_phone(db: Session, caller_phone: str) -> Lead:
    return db.query(Lead).filter(Lead.caller_phone == caller_phone).first()

def log_call(db: Session, call_sid: str, lead_id: int, transcript: str, summary: str, duration: int) -> CallLog:
    call_log = CallLog(
        call_sid=call_sid,
        lead_id=lead_id,
        transcript=transcript,
        summary=summary,
        duration_seconds=duration
    )
    db.add(call_log)
    db.commit()
    db.refresh(call_log)
    return call_log
