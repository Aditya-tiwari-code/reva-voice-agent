import pytest
from app.rag.retriever import PropertyRetriever
from app.router.llm_router import generate_natural_conversation


@pytest.fixture
def retriever():
    return PropertyRetriever()


def test_2bhk_ghaziabad_returns_only_2bhk(retriever):
    """
    Test 1: STRICT BHK FILTER
    When the user requests 2BHK in Ghaziabad under 50 lakh:
    - Filters extract bhk=2, city=Ghaziabad, transaction_type=buy, max_price=50.
    - Exact matching properties returned must strictly have bhk == 2.
    - Any alternative properties returned must be marked with is_alternative=True.
    - In the conversational response, alternative options are clearly placed
      under 'Nearby options in the same city:' and never mixed silently into exact matches.
    """
    query = "2BHK flat in Ghaziabad under 50 lakh"
    filters = retriever.extract_filters_from_text(query)

    assert filters["city"] == "Ghaziabad"
    assert filters["bhk"] == 2
    assert filters["transaction_type"] == "buy"
    assert filters["max_price"] == 50.0

    results = retriever.search(query, filters=filters, top_k=3)
    assert len(results) > 0, "Expected at least 1 result for Ghaziabad"

    exact_matches = [r for r in results if not r.get("is_alternative")]
    assert len(exact_matches) > 0, "Expected at least 1 exact 2BHK match in Ghaziabad"

    for prop in exact_matches:
        meta = prop.get("metadata", {})
        assert meta.get("bhk") == 2, f"Expected 2 BHK for exact match, got {meta.get('bhk')}"
        assert meta.get("city") == "Ghaziabad"
        assert meta.get("transaction_type") == "buy"

    # Any alternatives must be explicitly marked
    alternatives = [r for r in results if r.get("is_alternative")]
    for alt in alternatives:
        assert alt.get("is_alternative") is True

    # Check conversation output formats properly
    response = generate_natural_conversation(query, properties=results, language="hinglish")
    if alternatives:
        assert "Nearby options in the same city:" in response
        # Verify the exact section shows 2 BHK
        parts = response.split("Nearby options in the same city:")
        assert "2 BHK" in parts[0]


def test_rent_query_returns_only_rent_with_monthly_format(retriever):
    """
    Test 2: RENT QUERY & MONTHLY FORMAT
    When a rent query is issued:
    - transaction_type is extracted as 'rent'.
    - All returned properties must have transaction_type == 'rent'.
    - Rent is formatted as monthly rupees (e.g. '₹35,000/month'), never 'Lakh INR'.
    """
    query = "Flat for rent in Ghaziabad under 40 thousand"
    filters = retriever.extract_filters_from_text(query)

    assert filters["transaction_type"] == "rent"
    assert filters["city"] == "Ghaziabad"
    assert filters["max_price"] == 40.0  # interpreted as 40 thousand

    results = retriever.search(query, filters=filters, top_k=3)
    assert len(results) > 0, "Expected rental results in Ghaziabad"

    for prop in results:
        meta = prop.get("metadata", {})
        assert meta.get("transaction_type") == "rent", f"Expected rent, got {meta.get('transaction_type')}"

    # Verify context formatting for LLM
    context = retriever.format_results_for_llm(results)
    assert "/month" in context, f"Expected '/month' in context, got: {context}"
    assert "Lakh INR" not in context

    # Verify conversational bullet format
    response = generate_natural_conversation(query, properties=results, language="english")
    assert "/month" in response, f"Expected '/month' in response, got: {response}"
    assert "Lakh" not in response


def test_buy_query_returns_no_rent_rows(retriever):
    """
    Test 3: BUY QUERY RETURNS NO RENT ROWS & DEFAULTS TO BUY
    - If user does not say buy or rent, defaults to buy (is_default_transaction=True).
    - No rent properties must be returned for buy queries.
    - Default buy conversation mentions that rental options are also available.
    """
    query = "2BHK flat in Ghaziabad under 50 lakh"
    filters = retriever.extract_filters_from_text(query)

    assert filters["transaction_type"] == "buy"
    assert filters["is_default_transaction"] is True

    results = retriever.search(query, filters=filters, top_k=3)
    for prop in results:
        meta = prop.get("metadata", {})
        assert meta.get("transaction_type") == "buy", f"Expected buy property, got {meta.get('transaction_type')}"
        assert meta.get("transaction_type") != "rent"

    # Conversational response includes rental availability note when defaulted
    response = generate_natural_conversation(
        query,
        properties=results,
        language="hinglish",
        is_default_transaction=True
    )
    lower_resp = response.lower()
    assert ("rent" in lower_resp or "rental" in lower_resp or "kiraye" in lower_resp), (
        "Expected mention of rental options when query defaults to buy"
    )


def test_city_with_no_listing_says_so_honestly(retriever):
    """
    Test 4: HONEST MESSAGE FOR CITY WITH NO LISTING
    When a city has no listings in ChromaDB:
    - search() returns an empty list (does not silently return random city results).
    - The assistant honestly states no listings exist in that city and suggests nearby alternatives (e.g. Noida).
    """
    query = "3BHK flat in Lucknow under 60 lakh"
    filters = retriever.extract_filters_from_text(query)

    assert filters["city"] == "Lucknow"

    results = retriever.search(query, filters=filters, top_k=3)
    assert len(results) == 0, f"Expected 0 results for unlisted city, got {len(results)}"

    response = generate_natural_conversation(query, properties=results, language="english")
    lower_resp = response.lower()

    assert "lucknow" in lower_resp, "Expected mentioned city in response"
    assert "no listings" in lower_resp or "don't have any listings" in lower_resp or "not have" in lower_resp
    assert "noida" in lower_resp, "Expected nearby Noida suggestions"

