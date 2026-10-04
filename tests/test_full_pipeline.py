import pytest
from app.agent.conversation import ConversationAgent
from app.rag.retriever import PropertyRetriever

@pytest.fixture
def agent():
    return ConversationAgent()

@pytest.fixture
def retriever():
    return PropertyRetriever()


# ==========================================
# 1. 10 SAMPLE HINGLISH QUERIES FULL PIPELINE TEST
# ==========================================
SAMPLE_QUERIES = [
    {
        "query": "Noida mein 2BHK chahiye, budget 50 lakh hai",
        "expected_complexity": "simple",
        "expected_model": "groq_llama3"
    },
    {
        "query": "Sector 62 mein koi flat available hai kya",
        "expected_complexity": "simple",
        "expected_model": "groq_llama3"
    },
    {
        "query": "Mujhe 3BHK villa dekhna hai, rent pe",
        "expected_complexity": "simple",
        "expected_model": "groq_llama3"
    },
    {
        "query": "Ye property ka price negotiate ho sakta hai kya",
        "expected_complexity": "complex",
        "expected_model": "gemini_flash"
    },
    {
        "query": "Site visit book karni hai kal ke liye",
        "expected_complexity": "simple",
        "expected_model": "groq_llama3"
    },
    {
        "query": "Compare karo Noida vs Gurgaon flats",
        "expected_complexity": "complex",
        "expected_model": "gemini_flash"
    },
    {
        "query": "Metro ke paas koi option hai?",
        "expected_complexity": "simple",
        "expected_model": "groq_llama3"
    },
    {
        "query": "What is the price of 2BHK in Sector 76",
        "expected_complexity": "simple",
        "expected_model": "groq_llama3"
    },
    {
        "query": "Kitne sqft ka flat hai yeh",
        "expected_complexity": "simple",
        "expected_model": "groq_llama3"
    },
    {
        "query": "Manager se baat karni hai",
        "expected_complexity": "complex",
        "expected_model": "gemini_flash"
    }
]

def test_full_pipeline_10_samples(agent):
    for idx, item in enumerate(SAMPLE_QUERIES, 1):
        session_id = f"test_full_pipeline_sess_{idx}"
        query = item["query"]
        expected_model = item["expected_model"]

        result = agent.process_text_input(session_id, query)

        assert result["response_text"], f"Response text should not be empty for query: {query}"
        assert result["model_used"] == expected_model, f"Expected {expected_model} but got {result['model_used']} for query: {query}"
        assert 0 <= result["lead_score"] <= 100, f"Lead score out of bounds (0-100) for query: {query}"
        assert "language" in result
        assert "intent" in result


# ==========================================
# 2. RAG RETRIEVAL ACCURACY TEST (10 Queries)
# ==========================================
RAG_TEST_CASES = [
    {"query": "3BHK apartment in Gachibowli Hyderabad", "expected_city": "Hyderabad"},
    {"query": "Greek style 2BHK in Bangalore near ORR", "expected_city": "Bangalore"},
    {"query": "Ultra-luxury 4BHK penthouse in Gurgaon DLF", "expected_city": "Gurgaon"},
    {"query": "Eco-friendly 2BHK in Sector 43 Noida", "expected_city": "Noida"},
    {"query": "3BHK high rise apartment in Lower Parel Mumbai", "expected_city": "Mumbai"},
    {"query": "4BHK in Kharadi Pune near EON Free Zone", "expected_city": "Pune"},
    {"query": "Affordable 2BHK in Velachery Chennai", "expected_city": "Chennai"},
    {"query": "3BHK duplex villa in New Town Kolkata", "expected_city": "Kolkata"},
    {"query": "Studio apartment for rent in Rajajinagar Bangalore", "expected_city": "Bangalore"},
    {"query": "2BHK apartment in Powai with lake view rent", "expected_city": "Mumbai"}
]

def test_rag_retrieval_accuracy(retriever):
    success_count = 0
    for case in RAG_TEST_CASES:
        filters = retriever.extract_filters_from_text(case["query"])
        results = retriever.search(case["query"], filters=filters, top_k=3)
        assert len(results) > 0, f"No properties found for query: {case['query']}"
        
        # Check if top results match expected city
        top_cities = [res.get("metadata", {}).get("city") for res in results]
        if case["expected_city"] in top_cities:
            success_count += 1

    accuracy = success_count / len(RAG_TEST_CASES)
    assert accuracy >= 0.8, f"RAG retrieval accuracy {accuracy*100}% below 80% threshold"
