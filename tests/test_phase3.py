import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.models import Base, get_db, Lead, Call, ConversationTurn
from app.db import crud
from app.telephony.twilio_handler import TwilioHandler
from app.agent.conversation import ConversationAgent

# Test DB Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_reva.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    yield db
    db.close()


# ==========================================
# 1. DATABASE CRUD TESTS
# ==========================================
def test_crud_create_and_update_lead(db_session):
    session_id = f"test_sess_lead_{uuid.uuid4()}"
    lead = crud.create_lead(db_session, session_id=session_id, phone="+919876543210")
    assert lead.session_id == session_id
    assert lead.caller_phone == "+919876543210"

    updated = crud.update_lead(db_session, session_id=session_id, lead_score=80, status="qualified", location_pref="Bangalore")
    assert updated.lead_score == 80
    assert updated.status == "qualified"
    assert updated.location_pref == "Bangalore"


def test_crud_log_turn_and_analytics(db_session):
    session_id = f"test_sess_turn_{uuid.uuid4()}"
    crud.create_lead(db_session, session_id=session_id)
    crud.create_call(db_session, session_id=session_id)

    turn_data = {
        "user_text": "Need 3BHK in Gurgaon",
        "language": "english",
        "intent": "property_details",
        "complexity": "simple",
        "model_used": "groq_llama3",
        "response_text": "Here are 3BHK listings in Gurgaon",
        "latency_ms": 250.0,
        "estimated_cost_usd": 0.00008
    }

    turn = crud.log_turn(db_session, session_id=session_id, turn_data=turn_data)
    assert turn.turn_number == 1
    assert turn.model_used == "groq_llama3"

    call = crud.end_call(db_session, session_id=session_id, outcome="completed")
    assert call.total_turns == 1
    assert call.total_cost_usd == 0.00008

    analytics = crud.get_analytics_summary(db_session)
    assert analytics["total_calls"] > 0
    assert "groq_llama3" in analytics["model_distribution"]


# ==========================================
# 2. FASTAPI REST ENDPOINTS TESTS
# ==========================================
def test_endpoint_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0"}


def test_endpoint_chat_text():
    payload = {
        "session_id": "test_rest_sess_200",
        "text": "What is the price of 2BHK flat in Bangalore?",
        "phone": "+919999988888"
    }
    response = client.post("/chat/text", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response_text" in data
    assert "lead_score" in data
    assert data["session_id"] == "test_rest_sess_200"


def test_endpoint_get_leads():
    response = client.get("/leads")
    assert response.status_code == 200
    leads = response.json()
    assert isinstance(leads, list)
    assert len(leads) > 0


def test_endpoint_analytics_summary():
    response = client.get("/analytics/summary")
    assert response.status_code == 200
    summary = response.json()
    assert "total_calls" in summary
    assert "avg_lead_score" in summary


# ==========================================
# 3. TWILIO TWIML GENERATOR TESTS
# ==========================================
def test_twilio_handler_greeting():
    handler = TwilioHandler()
    twiml = handler.generate_greeting_twiml()
    assert "<?xml version=" in twiml
    assert "Namaste! Main REVA hoon" in twiml
    assert "<Gather" in twiml


def test_twilio_handler_escalation():
    handler = TwilioHandler()
    twiml = handler.generate_escalation_twiml(agent_phone="+919876543210")
    assert "<Dial>+919876543210</Dial>" in twiml
    assert "connect kar raha hoon" in twiml


def test_twilio_handler_booking():
    handler = TwilioHandler()
    twiml = handler.generate_booking_twiml(property_name="Sobha Neopolis", date="Tomorrow 10 AM")
    assert "Sobha Neopolis" in twiml
    assert "Tomorrow 10 AM" in twiml


# ==========================================
# 4. HUMAN ESCALATION LOGIC TESTS
# ==========================================
def test_escalation_keywords():
    agent = ConversationAgent()
    payload = {
        "user_text": "I want to talk to a human manager right now",
        "intent": "unknown",
        "lead_score": 20
    }
    assert agent.should_escalate(payload) is True


def test_escalation_high_lead_score_site_visit():
    agent = ConversationAgent()
    payload = {
        "user_text": "Book site visit for 3BHK flat in Whitefield Bangalore",
        "intent": "site_visit_request",
        "lead_score": 80
    }
    assert agent.should_escalate(payload) is True


def test_escalation_duration_limit():
    agent = ConversationAgent()
    payload = {
        "user_text": "Just looking around",
        "intent": "greeting",
        "lead_score": 0,
        "duration_seconds": 650
    }
    assert agent.should_escalate(payload) is True


def test_escalation_consecutive_negotiations():
    agent = ConversationAgent()
    sess_id = "test_escalate_sess"
    
    # Process turn 1: negotiation
    agent.process_text_input(sess_id, "Price thoda kam karo best price batao")
    # Process turn 2: negotiation
    res2 = agent.process_text_input(sess_id, "Discount do final rate negotiate karo")
    
    assert res2["should_escalate"] is True
