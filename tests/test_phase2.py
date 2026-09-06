import pytest
from unittest.mock import MagicMock, patch
from app.rag.retriever import PropertyRetriever
from app.router.llm_router import AdaptiveLLMRouter
from app.agent.conversation import ConversationAgent


@pytest.fixture
def retriever():
    return PropertyRetriever()


@pytest.fixture
def router():
    return AdaptiveLLMRouter(groq_api_key="mock_groq_key", gemini_api_key="mock_gemini_key")


@pytest.fixture
def agent():
    return ConversationAgent()


# ==========================================
# 1. PROPERTY EMBEDDING & RETRIEVAL TESTS (5 Queries)
# ==========================================
def test_retrieval_query_1_gachibowli(retriever):
    filters = retriever.extract_filters_from_text("3BHK apartment in Gachibowli Hyderabad")
    assert filters["city"] == "Hyderabad"
    assert filters["property_type"] == "Apartment"


def test_retrieval_query_2_bangalore_budget(retriever):
    filters = retriever.extract_filters_from_text("2BHK flat in Bangalore under 100 lakhs")
    assert filters["city"] == "Bangalore"
    assert filters["property_type"] == "Apartment"
    assert filters["max_price"] == 100.0


def test_retrieval_query_3_gurgaon_penthouse(retriever):
    filters = retriever.extract_filters_from_text("Luxury penthouse in Gurgaon")
    assert filters["city"] == "Gurgaon"
    assert filters["property_type"] == "Penthouse"


def test_retrieval_query_4_pune_villa(retriever):
    filters = retriever.extract_filters_from_text("Villa in Pune with private garden")
    assert filters["city"] == "Pune"
    assert filters["property_type"] == "Villa"


def test_retrieval_query_5_powai_rent(retriever):
    filters = retriever.extract_filters_from_text("Flat for rent in Powai Mumbai")
    assert filters["city"] == "Mumbai"
    assert filters["transaction_type"] == "rent"


# ==========================================
# 2. DYNAMIC LLM ROUTER TESTS (Mocked APIs)
# ==========================================
def test_router_simple_query(router):
    result = router.route(
        text="What is the price of 2BHK in Bangalore?",
        complexity="simple",
        context="Property 1: 2BHK in Bangalore. Price 95 Lakh."
    )
    assert result["model_used"] == "groq_llama3"
    assert "response_text" in result
    assert result["tokens_used"] > 0
    assert result["latency_ms"] >= 0.0


def test_router_complex_query(router):
    result = router.route(
        text="Compare Sobha Neopolis and Prestige High Fields in detail and negotiate price",
        complexity="complex",
        context="Property 1: Sobha Neopolis. Property 2: Prestige High Fields."
    )
    assert result["model_used"] == "gemini_flash"
    assert "response_text" in result
    assert result["tokens_used"] > 0


def test_router_cost_calculation(router):
    groq_cost = router.calculate_cost("groq_llama3", 1000)
    assert groq_cost == 0.00008

    gemini_cost = router.calculate_cost("gemini_flash", 1000)
    assert gemini_cost == 0.00015


# ==========================================
# 3. LEAD SCORING TESTS (4 Sample Session Dicts)
# ==========================================
def test_lead_score_full_qualification(agent):
    session_data = {
        "user_text": "I want a 3BHK flat in Bangalore under 100 lakh ASAP and want to book site visit",
        "filters_extracted": {"city": "Bangalore", "property_type": "Apartment", "max_price": 100.0},
        "intent": "site_visit_request"
    }
    score = agent.get_lead_score(session_data)
    assert score == 100


def test_lead_score_partial_qualification_60(agent):
    session_data = {
        "user_text": "Looking for 2BHK flat in Gurgaon budget 80 lakhs",
        "filters_extracted": {"city": "Gurgaon", "property_type": "Apartment", "max_price": 80.0},
        "intent": "price_inquiry"
    }
    score = agent.get_lead_score(session_data)
    assert score == 60


def test_lead_score_partial_qualification_40(agent):
    session_data = {
        "user_text": "Kahan hai ye property dekhe site visit karni hai",
        "filters_extracted": {"city": None, "property_type": None, "max_price": None},
        "intent": "site_visit_request"
    }
    score = agent.get_lead_score(session_data)
    assert score == 40


def test_lead_score_low_intent_0(agent):
    session_data = {
        "user_text": "Hello good morning",
        "filters_extracted": {"city": None, "property_type": None, "max_price": None},
        "intent": "greeting"
    }
    score = agent.get_lead_score(session_data)
    assert score == 0
