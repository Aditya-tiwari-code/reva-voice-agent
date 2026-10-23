import pytest
from app.rag.retriever import PropertyRetriever

RAG_BENCHMARK_CASES = [
    {
        "query": "3BHK apartment in Gachibowli Hyderabad",
        "expected_title": "Prestige High Fields",
        "expected_city": "Hyderabad"
    },
    {
        "query": "Greek style 2BHK in Bangalore near ORR",
        "expected_title": "Sobha Neopolis",
        "expected_city": "Bangalore"
    },
    {
        "query": "Ultra-luxury 4BHK penthouse in Gurgaon DLF",
        "expected_title": "DLF The Aralias Penthouse",
        "expected_city": "Gurgaon"
    },
    {
        "query": "Eco-friendly 2BHK in Sector 43 Noida",
        "expected_title": "Godrej Woods",
        "expected_city": "Noida"
    },
    {
        "query": "3BHK high rise apartment in Lower Parel Mumbai",
        "expected_title": "Lodha World One",
        "expected_city": "Mumbai"
    },
    {
        "query": "4BHK in Kharadi Pune near EON Free Zone",
        "expected_title": "Panchshil Towers",
        "expected_city": "Pune"
    },
    {
        "query": "Affordable 2BHK in Velachery Chennai",
        "expected_title": "Casagrand Premier",
        "expected_city": "Chennai"
    },
    {
        "query": "3BHK duplex villa in New Town Kolkata",
        "expected_title": "PS Navyom 3BHK Villa",
        "expected_city": "Kolkata"
    },
    {
        "query": "Studio apartment for rent in Rajajinagar Bangalore",
        "expected_title": "Brigade Gateway 1BHK Studio",
        "expected_city": "Bangalore"
    },
    {
        "query": "2BHK apartment in Powai with lake view rent",
        "expected_title": "Hiranandani Gardens 2BHK",
        "expected_city": "Mumbai"
    }
]

def test_rag_top_3_retrieval_accuracy():
    """
    RAG Accuracy Test: For 10 property search queries, check if the
    correct property appears in the top-3 results.
    """
    retriever = PropertyRetriever()
    correct_retrievals = 0
    total_queries = len(RAG_BENCHMARK_CASES)

    for case in RAG_BENCHMARK_CASES:
        filters = retriever.extract_filters_from_text(case["query"])
        results = retriever.search(case["query"], filters=filters, top_k=3)

        assert len(results) > 0, f"Query '{case['query']}' returned no results"

        top_titles = [r.get("metadata", {}).get("title", "") for r in results]
        top_cities = [r.get("metadata", {}).get("city", "") for r in results]

        # Check match by title substring or city
        title_found = any(case["expected_title"].lower() in t.lower() for t in top_titles)
        city_found = case["expected_city"].lower() in [c.lower() for c in top_cities]

        if title_found or city_found:
            correct_retrievals += 1

    accuracy = (correct_retrievals / total_queries) * 100.0
    print(f"\nRAG Accuracy: {correct_retrievals}/{total_queries} ({accuracy:.1f}%)")
    assert accuracy >= 80.0, f"RAG accuracy {accuracy}% below 80% threshold"
