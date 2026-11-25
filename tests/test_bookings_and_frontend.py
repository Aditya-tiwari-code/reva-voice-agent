from unittest.mock import MagicMock
from pathlib import Path
import pytest
from fastapi import HTTPException

from app.db.models import init_db, SessionLocal
from app.db import crud
from app.agent.conversation import ConversationAgent
from app.main import BookingRequest, create_booking, get_bookings, get_featured_properties, root

def run_coro(coro):
    """Execute coroutine synchronously without event loop or external socket portals."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_process_text_input_includes_properties_array():
    """
    Backend requirement: Conversation agent output must include a 'properties' array
    with standard keys for frontend cards without removing existing fields.
    """
    agent = ConversationAgent()
    mock_groq = MagicMock()
    mock_comp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Namaste! Here are verified options in Ghaziabad."
    mock_comp.choices = [mock_choice]
    mock_comp.usage.total_tokens = 25
    mock_groq.chat.completions.create.return_value = mock_comp
    agent.router._groq_client = mock_groq

    res = agent.process_text_input("sess_test_1", "2BHK flat in Ghaziabad under 50 lakh")

    # Preserved existing fields
    assert "response_text" in res
    assert "properties_found" in res
    assert "lead_score" in res

    # New 'properties' array
    assert "properties" in res
    assert isinstance(res["properties"], list)
    assert len(res["properties"]) > 0

    first_prop = res["properties"][0]
    expected_keys = [
        "id", "title", "location", "city", "price_lakh",
        "bhk", "area_sqft", "transaction_type", "availability", "amenities"
    ]
    for k in expected_keys:
        assert k in first_prop, f"Key '{k}' missing from property"
    assert first_prop["bhk"] == 2
    assert first_prop["city"] == "Ghaziabad"
    assert first_prop["transaction_type"] == "buy"


def test_post_and_get_bookings(db):
    """
    Backend requirement:
    - POST /bookings validates phone, saves to SQLite site_visits table, updates lead status to 'booked'.
    - GET /bookings returns all bookings.
    """
    # 1. Invalid phone should raise HTTPException 400
    bad_req = BookingRequest(
        name="Rohan Gupta",
        phone="123",  # Invalid short phone
        property_id="31",
        preferred_date="2026-11-05",
        preferred_time="Afternoon (1 PM - 3 PM)",
        session_id="sess_test_booking_1"
    )
    with pytest.raises(HTTPException) as exc_info:
        run_coro(create_booking(bad_req, db))
    assert exc_info.value.status_code == 400

    # 2. Valid booking
    good_req = BookingRequest(
        name="Rohan Gupta",
        phone="9876543210",
        property_id="31",
        preferred_date="2026-11-05",
        preferred_time="Afternoon (1 PM - 3 PM)",
        session_id="sess_test_booking_1"
    )
    data = run_coro(create_booking(good_req, db))
    assert data["status"] == "success"
    assert "booking" in data
    assert data["booking"]["name"] == "Rohan Gupta"
    assert data["booking"]["phone"] == "9876543210"

    # Verify lead status was updated to booked
    lead = crud.get_lead_by_session(db, "sess_test_booking_1")
    assert lead is not None
    assert lead.status == "booked"

    # 3. GET /bookings includes the new booking
    bookings = run_coro(get_bookings(db))
    assert any(b.name == "Rohan Gupta" for b in bookings)


def test_root_serves_new_website():
    """
    Requirement: Root '/' must serve static/index.html with the upgraded website.
    """
    res = run_coro(root())
    assert Path(res.path).name == "index.html"
    content = Path(res.path).read_text(encoding="utf-8")
    assert "Apna ghar dhundo" in content
    assert "chatPanel" in content
    assert "bookingModal" in content
    assert "emiModal" in content


def test_backup_chat_served_at_static():
    """
    Requirement: Keep current chat page at /static/test_chat.html as a backup.
    """
    static_chat = Path("static/test_chat.html")
    assert static_chat.exists()
    content = static_chat.read_text(encoding="utf-8")
    assert "REVA AI Assistant" in content


def test_featured_properties_endpoint():
    """
    Requirement: Featured listings showcase on landing page.
    """
    featured = run_coro(get_featured_properties())
    assert isinstance(featured, list)
    assert len(featured) > 0
    first = featured[0]
    assert "title" in first
    assert "price_lakh" in first
    assert "transaction_type" in first
