from unittest.mock import MagicMock
import pytest
from app.tools.financial_tools import (
    calculate_emi,
    estimate_affordability,
    compare_properties,
    get_site_visit_checklist,
    parse_and_calculate_emi,
    parse_and_estimate_affordability
)
from app.agent.conversation import ConversationAgent

@pytest.fixture
def agent():
    ag = ConversationAgent()
    mock_reply = '{"reply_text": "Here are 2BHK flats in Noida.", "spoken_text": "I found a few options in Noida.", "language": "en", "intent": "property_inquiry", "slots": {"bhk": 2, "city": "Noida", "budget": 60.0, "buy_or_rent": "buy", "timeline": null}, "next_action": "show_properties"}'
    ag.router._call_groq = MagicMock(return_value=(mock_reply, 30, "llama-3-8b-8192"))
    ag.router._call_gemini = MagicMock(return_value=(mock_reply, 30, "gemini-1.5-flash"))
    return ag


def test_emi_calculation_formula():
    """Verify standard EMI formula in Python code: 60 lakh, 20 yrs, 8.5%."""
    res = calculate_emi(principal_lakh=60.0, tenure_years=20, annual_interest_rate=8.5)
    # P = 60,00,000, r = 0.085 / 12 = 0.0070833, n = 240
    # Expected EMI ~ 52,069
    assert res["emi_monthly"] > 50000 and res["emi_monthly"] < 54000
    assert "₹52,069" in res["text_summary"] or res["emi_monthly"] == 52069
    assert "52,069" in res["spoken_summary_en"]
    assert "text_summary" in res
    assert "spoken_summary_hi" in res


def test_parse_and_calculate_emi():
    """Verify natural query parsing for EMI."""
    query = "What is the monthly EMI for 40 lakh for 15 years at 9%?"
    res = parse_and_calculate_emi(query)
    assert res is not None
    assert res["principal_lakh"] == 40.0
    assert res["tenure_years"] == 15
    assert res["annual_interest_rate"] == 9.0
    assert res["emi_monthly"] > 0


def test_affordability_estimation():
    """Verify affordability calculation based on 45% FOIR."""
    # Monthly salary 1,00,000, no existing EMI, 10 lakh down payment
    res = estimate_affordability(monthly_income=100000, existing_emis=0, down_payment_lakh=10.0)
    assert res["max_recommended_emi"] == 45000
    assert res["estimated_loan_lakh"] > 45.0
    assert res["budget_range_max_lakh"] > 55.0


def test_property_comparison():
    """Verify side-by-side property comparison with price diff and rate per sqft."""
    prop1 = {
        "title": "Gaur City 2", "price_lakh": 55.0, "area_sqft": 1050,
        "location": "Greater Noida West", "city": "Noida", "bhk": 2
    }
    prop2 = {
        "title": "Supertech Capetown", "price_lakh": 65.0, "area_sqft": 1150,
        "location": "Sector 74", "city": "Noida", "bhk": 2
    }
    res = compare_properties(prop1, prop2)
    assert res["price_diff_lakh"] == 10.0
    assert "Property Comparison" in res["table_markdown"]
    assert "Gaur City 2" in res["table_markdown"]
    assert "Supertech Capetown" in res["table_markdown"]


def test_site_visit_checklist():
    """Verify site visit checklist mentions RERA portal verification without fake numbers."""
    chk = get_site_visit_checklist()
    assert "RERA" in chk["checklist_text"]
    assert "Carpet area" in chk["checklist_text"] or "carpet area" in chk["checklist_text"]


def test_agent_emi_tool_direct_execution(agent):
    """Verify ConversationAgent executes Python EMI tool directly with zero LLM tokens."""
    res = agent.process_text_input("sess_emi_test", "What is the EMI for 50 lakh for 20 years at 8.5%?")
    assert res["model_used"] == "python_emi_tool"
    assert res["tokens_used"] == 0
    assert "Home Loan EMI Calculation" in res["reply_text"]
    assert "50" in res["reply_text"]


def test_agent_shortlist_feature(agent):
    """Verify shortlisting properties in session state."""
    sess_id = "sess_shortlist_test"

    # Search first
    agent.process_text_input(sess_id, "Show 2BHK flats in Noida under 60 lakh")

    # Save to shortlist
    res_save = agent.process_text_input(sess_id, "Save this one to my shortlist")
    assert res_save["model_used"] == "python_shortlist_tool"
    assert res_save["shortlist_count"] >= 1

    # Retrieve shortlist
    res_show = agent.process_text_input(sess_id, "Show my shortlist")
    assert res_show["model_used"] == "python_shortlist_tool"
    assert "shortlist" in res_show["reply_text"].lower()


def test_agent_lead_category_scoring(agent):
    """Verify hot/warm/cold lead categorization."""
    sess_id = "sess_lead_cat_test"

    # Turn with location, budget, bhk, timeline, and site visit -> high score -> hot
    res = agent.process_text_input(sess_id, "I want to buy 2BHK flat in Noida under 60 lakh urgent this month and book site visit kal subah")
    assert res["lead_category"] == "hot"
    assert "lead_reason" in res
