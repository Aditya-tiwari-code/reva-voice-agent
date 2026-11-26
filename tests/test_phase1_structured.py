import re
from unittest.mock import MagicMock
import pytest
from app.agent.conversation import ConversationAgent
from app.router.llm_router import build_spoken_text, parse_structured_llm_response

@pytest.fixture
def agent():
    ag = ConversationAgent()
    mock_reply = '{"reply_text": "Here are 2BHK flats in Ghaziabad.", "spoken_text": "I found a few 2BHK options in Ghaziabad. Have a look at them below.", "language": "en", "intent": "property_inquiry", "slots": {"bhk": 2, "city": "Ghaziabad", "budget": 50.0, "buy_or_rent": "buy", "timeline": null}, "next_action": "show_properties"}'
    ag.router._call_groq = MagicMock(return_value=(mock_reply, 30, "llama-3-8b-8192"))
    ag.router._call_gemini = MagicMock(return_value=(mock_reply, 30, "gemini-1.5-flash"))
    return ag

def test_structured_json_response_keys(agent):
    """
    Phase 1 Requirement 2:
    Response must include reply_text, spoken_text, language, intent, slots, and next_action.
    """
    res = agent.process_text_input("sess_p1_1", "I want a 2BHK flat in Ghaziabad under 50 lakh")
    
    assert "reply_text" in res
    assert "spoken_text" in res
    assert "language" in res
    assert "intent" in res
    assert "slots" in res
    assert "next_action" in res

    # Check slots structure
    slots = res["slots"]
    assert isinstance(slots, dict)
    assert slots.get("bhk") == 2
    assert slots.get("city") == "Ghaziabad"
    assert slots.get("budget") == 50.0
    assert slots.get("buy_or_rent") == "buy"

    # Backward compatibility: response_text must equal reply_text
    assert res["response_text"] == res["reply_text"]

def test_language_session_mirroring(agent):
    """
    Phase 1 Requirement 1:
    Detect user's language per message and keep in session state, mirroring it across turns.
    """
    sess_id = "sess_p1_lang_mirror"
    
    # Turn 1: User speaks in Hindi (Devanagari)
    res1 = agent.process_text_input(sess_id, "नमस्ते, मुझे दिल्ली में 2BHK फ्लैट चाहिए")
    assert res1["language"] == "hindi"
    assert agent.session_states[sess_id]["language"] == "hindi"

    # Turn 2: User responds with a neutral short confirmation ("theek hai")
    res2 = agent.process_text_input(sess_id, "theek hai")
    # Should mirror Hindi from session state
    assert res2["language"] == "hindi"

    # Turn 3: User explicitly switches to English
    res3 = agent.process_text_input(sess_id, "What about options in Noida under 60 lakh?")
    assert res3["language"] == "english"
    assert agent.session_states[sess_id]["language"] == "english"

def test_spoken_text_rules():
    """
    Phase 1 Requirement 4:
    spoken_text rules: max 2-3 short sentences, never read full property list bullets,
    Devanagari for Hindi & Hinglish, ends with next step.
    """
    dummy_props = [{
        "metadata": {"title": "Apex Golf Avenue", "city": "Noida", "bhk": 2, "price_lakh": 45.0, "transaction_type": "buy"}
    }]

    # English
    en_spoken = build_spoken_text(
        reply_text="• Apex Golf Avenue — 2 BHK | 45 Lakh",
        language="english",
        properties=dummy_props,
        intent="property_inquiry"
    )
    assert "•" not in en_spoken
    sentence_count_en = len([s for s in re.split(r'[.?!]', en_spoken) if s.strip()])
    assert sentence_count_en <= 3
    assert "options" in en_spoken or "visit" in en_spoken

    # Hindi
    hi_spoken = build_spoken_text(
        reply_text="• Apex Golf Avenue — 2 BHK | 45 Lakh",
        language="hindi",
        properties=dummy_props,
        intent="property_inquiry"
    )
    assert bool(re.search(r'[\u0900-\u097F]', hi_spoken)), "Hindi spoken text must use Devanagari script"
    assert "•" not in hi_spoken

    # Hinglish
    hing_spoken = build_spoken_text(
        reply_text="• Apex Golf Avenue — 2 BHK | 45 Lakh",
        language="hinglish",
        properties=dummy_props,
        intent="property_inquiry"
    )
    assert bool(re.search(r'[\u0900-\u097F]', hing_spoken)), "Hinglish spoken text must be in Devanagari for natural Indian TTS"
    assert "•" not in hing_spoken

def test_safe_parsing_fallback():
    """
    Phase 1 Requirement 3:
    Validate and safely parse JSON; fall back gracefully to plain text if model returns bad output.
    """
    # Malformed / plain text LLM response
    bad_output = "Namaste! Here are 3 flats in Ghaziabad:\n• Flat 1\n• Flat 2\nWould you like to book a visit?"
    parsed = parse_structured_llm_response(
        raw_text=bad_output,
        default_language="hinglish",
        default_intent="property_inquiry",
        properties=[{"metadata": {"city": "Ghaziabad", "bhk": 2}}],
        user_text="2BHK in Ghaziabad"
    )

    assert parsed["reply_text"] == bad_output
    assert parsed["spoken_text"] != ""
    assert "•" not in parsed["spoken_text"]
    assert parsed["language"] == "hinglish"
    assert parsed["next_action"] == "show_properties"
