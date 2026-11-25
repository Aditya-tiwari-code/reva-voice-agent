import pytest
from app.rag.retriever import PropertyRetriever

@pytest.fixture(scope="module")
def retriever():
    return PropertyRetriever()

def test_delhi_rental_dataset_query(retriever):
    """
    Test that queries for Delhi rentals search and find properties from Indian_housing_Delhi_data.csv.
    """
    query = "rent 1 RK or studio apartment in Kalkaji Delhi"
    filters = retriever.extract_filters_from_text(query)

    assert filters["city"] == "Delhi"
    assert filters["transaction_type"] == "rent"

    results = retriever.search(query, filters=filters, top_k=3)
    assert len(results) > 0, "Expected rental results in Delhi"
    for r in results:
        meta = r.get("metadata", {})
        assert meta.get("transaction_type") == "rent"
        assert meta.get("city") == "Delhi"

def test_faridabad_buy_dataset_query(retriever):
    """
    Test that queries for Faridabad buy listings search and find properties from real_estate_main.csv.
    """
    query = "flat for sale in Faridabad"
    filters = retriever.extract_filters_from_text(query)

    assert filters["city"] == "Faridabad"
    assert filters["transaction_type"] == "buy"

    results = retriever.search(query, filters=filters, top_k=3)
    assert len(results) > 0, "Expected buy results in Faridabad"
    for r in results:
        meta = r.get("metadata", {})
        assert meta.get("transaction_type") == "buy"
        assert meta.get("city") == "Faridabad"

def test_gurgaon_buy_dataset_query(retriever):
    """
    Test that queries for Gurgaon buy listings search and find properties from real_estate_main.csv.
    """
    query = "3BHK flat in DLF Gurgaon"
    filters = retriever.extract_filters_from_text(query)

    assert filters["city"] == "Gurgaon"
    assert filters["bhk"] == 3
    assert filters["transaction_type"] == "buy"

    results = retriever.search(query, filters=filters, top_k=3)
    assert len(results) > 0, "Expected 3BHK buy results in Gurgaon"
    exact_matches = [r for r in results if not r.get("is_alternative")]
    for r in exact_matches:
        meta = r.get("metadata", {})
        assert meta.get("bhk") == 3
        assert meta.get("city") == "Gurgaon"
        assert meta.get("transaction_type") == "buy"

def test_locality_to_city_mapping(retriever):
    """
    Test that popular Delhi NCR localities automatically map to their respective cities.
    """
    f_saket = retriever.extract_filters_from_text("2BHK flat in Saket under 40k rent")
    assert f_saket["city"] == "Delhi"
    assert f_saket["transaction_type"] == "rent"

    f_dwarka = retriever.extract_filters_from_text("3BHK in Dwarka")
    assert f_dwarka["city"] == "Delhi"

    f_sohna = retriever.extract_filters_from_text("flat for sale in Sohna Road")
    assert f_sohna["city"] == "Gurgaon"

    f_gn = retriever.extract_filters_from_text("villa in Greater Noida")
    assert f_gn["city"] == "Noida"

