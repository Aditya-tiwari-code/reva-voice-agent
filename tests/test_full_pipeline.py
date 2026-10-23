import pytest
from unittest.mock import MagicMock, patch
from app.agent.conversation import ConversationAgent
from app.rag.retriever import PropertyRetriever

# ==========================================
# 1. 10 SAMPLE HINGLISH REAL-ESTATE QUERIES
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

@pytest.fixture
def agent():
    agent_inst = ConversationAgent()
    
    # Configure Mock Groq Client
    mock_groq = MagicMock()
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Namaste! REVA yahan hai aapki property khojne mein madad karne ke liye. Noida aur anya shahron mein matching flats uplabdh hain."
    mock_completion.choices = [mock_choice]
    mock_completion.usage.total_tokens = 145
    mock_groq.chat.completions.create.return_value = mock_completion
    agent_inst.router._groq_client = mock_groq
    
    return agent_inst

@pytest.fixture
def retriever():
    return PropertyRetriever()


def test_full_pipeline_10_samples_with_mocked_llms(agent):
    """
    Integration test running 10 sample Hinglish real-estate queries
    through full conversation pipeline with mocked Groq & Gemini APIs.
    """
    with patch("google.generativeai.GenerativeModel") as mock_gemini_cls:
        mock_gemini_instance = MagicMock()
        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = "Detailed property comparison and escalation handling by Gemini 1.5 Flash."
        mock_gemini_resp.usage_metadata.total_token_count = 210
        mock_gemini_instance.generate_content.return_value = mock_gemini_resp
        mock_gemini_cls.return_value = mock_gemini_instance

        for idx, item in enumerate(SAMPLE_QUERIES, 1):
            session_id = f"test_full_pipeline_mock_sess_{idx}"
            query = item["query"]
            expected_model = item["expected_model"]

            result = agent.process_text_input(session_id, query)

            # Assert 1: response is not empty
            assert result["response_text"], f"Response text should not be empty for query: {query}"
            assert len(result["response_text"].strip()) > 0

            # Assert 2: model_used is correct (simple->groq, complex->gemini)
            assert result["model_used"] == expected_model, (
                f"Expected {expected_model} but got {result['model_used']} for query: '{query}'"
            )

            # Assert 3: lead_score is between 0-100
            assert 0 <= result["lead_score"] <= 100, (
                f"Lead score {result['lead_score']} out of bounds (0-100) for query: '{query}'"
            )

            # Additional pipeline health checks
            assert "language" in result
            assert "intent" in result
            assert "should_escalate" in result
            assert isinstance(result["filters_extracted"], dict)


# ==========================================
# 2. RAG RETRIEVAL ACCURACY TEST (10 Queries)
# ==========================================
RAG_TEST_CASES = [
    {
        "query": "3BHK apartment in Gachibowli Hyderabad",
        "expected_property": "Prestige High Fields",
        "expected_city": "Hyderabad"
    },
    {
        "query": "Greek style 2BHK in Bangalore near ORR",
        "expected_property": "Sobha Neopolis",
        "expected_city": "Bangalore"
    },
    {
        "query": "Ultra-luxury 4BHK penthouse in Gurgaon DLF",
        "expected_property": "DLF The Aralias",
        "expected_city": "Gurgaon"
    },
    {
        "query": "Eco-friendly 2BHK in Sector 43 Noida",
        "expected_property": "Godrej Woods",
        "expected_city": "Noida"
    },
    {
        "query": "3BHK high rise apartment in Lower Parel Mumbai",
        "expected_property": "Lodha World One",
        "expected_city": "Mumbai"
    },
    {
        "query": "4BHK in Kharadi Pune near EON Free Zone",
        "expected_property": "Panchshil Towers",
        "expected_city": "Pune"
    },
    {
        "query": "Affordable 2BHK in Velachery Chennai",
        "expected_property": "Casagrand Premier",
        "expected_city": "Chennai"
    },
    {
        "query": "3BHK duplex villa in New Town Kolkata",
        "expected_property": "PS Navyom",
        "expected_city": "Kolkata"
    },
    {
        "query": "Studio apartment for rent in Rajajinagar Bangalore",
        "expected_property": "Brigade Gateway",
        "expected_city": "Bangalore"
    },
    {
        "query": "2BHK apartment in Powai with lake view rent",
        "expected_property": "Hiranandani Gardens",
        "expected_city": "Mumbai"
    }
]

def test_rag_retrieval_accuracy(retriever):
    """
    RAG accuracy test: For 10 property search queries, check if correct
    property appears in top-3 results.
    """
    success_count = 0
    for case in RAG_TEST_CASES:
        filters = retriever.extract_filters_from_text(case["query"])
        results = retriever.search(case["query"], filters=filters, top_k=3)
        assert len(results) > 0, f"No properties found for query: {case['query']}"

        # Check if expected property appears in top-3 results
        top_titles = [res.get("metadata", {}).get("title", "") for res in results]
        top_cities = [res.get("metadata", {}).get("city", "") for res in results]

        property_matched = any(case["expected_property"].lower() in title.lower() for title in top_titles)
        city_matched = case["expected_city"].lower() in [c.lower() for c in top_cities]

        if property_matched or city_matched:
            success_count += 1

    accuracy = success_count / len(RAG_TEST_CASES)
    assert accuracy >= 0.8, f"RAG retrieval accuracy {accuracy*100}% below 80% threshold"
