import re
from typing import List, Dict, Any, Optional
import chromadb
from sentence_transformers import SentenceTransformer

class PropertyRetriever:
    """
    Handles semantic property search over ChromaDB with metadata filter extraction
    and prompt formatting for LLM context injection.
    """

    KNOWN_CITIES = {
        "bangalore": "Bangalore",
        "bengaluru": "Bangalore",
        "mumbai": "Mumbai",
        "pune": "Pune",
        "gurgaon": "Gurgaon",
        "gurugram": "Gurgaon",
        "noida": "Noida",
        "hyderabad": "Hyderabad",
        "chennai": "Chennai",
        "kolkata": "Kolkata",
        "delhi": "Delhi"
    }

    PROPERTY_TYPES = {
        "apartment": "Apartment",
        "flat": "Apartment",
        "villa": "Villa",
        "penthouse": "Penthouse",
        "studio": "Studio",
        "house": "Independent House"
    }

    def __init__(self, db_path: str = "./chroma_db", collection_name: str = "properties", model_name: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=db_path)
        self.model = SentenceTransformer(model_name)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def extract_filters_from_text(self, text: str) -> Dict[str, Optional[Any]]:
        """
        Extracts structured search filters from user text:
        - city
        - property_type
        - transaction_type ('buy' or 'rent')
        - max_price (in Lakhs)
        """
        if not text:
            return {"city": None, "property_type": None, "transaction_type": None, "max_price": None}

        lower_text = text.lower().strip()

        # 1. City extraction
        found_city = None
        for city_key, city_val in self.KNOWN_CITIES.items():
            if re.search(r'\b' + re.escape(city_key) + r'\b', lower_text):
                found_city = city_val
                break

        # 2. Property Type extraction
        found_prop_type = None
        for ptype_key, ptype_val in self.PROPERTY_TYPES.items():
            if re.search(r'\b' + re.escape(ptype_key) + r'\b', lower_text):
                found_prop_type = ptype_val
                break

        # 3. Transaction Type extraction ('buy' vs 'rent')
        found_trans_type = None
        if re.search(r'\b(rent|rental|lease|renting)\b', lower_text):
            found_trans_type = "rent"
        elif re.search(r'\b(buy|purchase|buying|sale)\b', lower_text):
            found_trans_type = "buy"

        # 4. Max Price extraction (e.g. "under 100 lakh", "budget 80 lakhs", "50 cr")
        found_max_price = None
        # Match patterns like: "under 100 lakh", "budget 150lakhs", "under 2 crore"
        price_match = re.search(r'(?:under|below|budget|within|around|upto)?\s*(\d+(?:\.\d+)?)\s*(lakhs?|lacs?|lac|crores?|cr|l)\b', lower_text)
        if price_match:
            val = float(price_match.group(1))
            unit = price_match.group(2)
            if unit in ["crore", "crores", "cr"]:
                val = val * 100.0  # Convert Crore to Lakhs
            found_max_price = val

        return {
            "city": found_city,
            "property_type": found_prop_type,
            "transaction_type": found_trans_type,
            "max_price": found_max_price
        }

    def search(self, query: str, filters: Dict[str, Any] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Embeds query text and retrieves top_k matching properties from ChromaDB
        with optional metadata filters.
        """
        if self.collection.count() == 0:
            return []

        query_embedding = self.model.encode(query).tolist()

        # Build ChromaDB metadata filter conditions
        where_conditions = []
        if filters:
            if filters.get("city"):
                where_conditions.append({"city": {"$eq": filters["city"]}})
            if filters.get("property_type"):
                where_conditions.append({"property_type": {"$eq": filters["property_type"]}})
            if filters.get("transaction_type"):
                where_conditions.append({"transaction_type": {"$eq": filters["transaction_type"]}})
            if filters.get("max_price") is not None:
                where_conditions.append({"price_lakh": {"$lte": filters["max_price"]}})

        where_clause = None
        if len(where_conditions) == 1:
            where_clause = where_conditions[0]
        elif len(where_conditions) > 1:
            where_clause = {"$and": where_conditions}

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause
            )
        except Exception:
            # Fallback to query without metadata filter if filtered query encounters error or no match
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

        # If zero matches found with strict where clause, fallback to unfiltered semantic search
        if not results or not results.get("ids") or len(results["ids"][0]) == 0:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

        matching_properties = []
        if results and results.get("ids") and len(results["ids"][0]) > 0:
            ids = results["ids"][0]
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
            documents = results["documents"][0] if results.get("documents") else [""] * len(ids)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

            for i in range(len(ids)):
                dist = distances[i]
                # Convert distance metric to similarity score 0-1 range
                sim_score = round(1.0 / (1.0 + dist), 4)
                matching_properties.append({
                    "id": ids[i],
                    "metadata": metadatas[i],
                    "document": documents[i],
                    "score": sim_score
                })

        return matching_properties

    def format_results_for_llm(self, properties: List[Dict[str, Any]]) -> str:
        """
        Formats retrieved properties into a concise string context for LLM prompt injection.
        """
        if not properties:
            return "No matching properties found in database."

        formatted_chunks = []
        for idx, prop in enumerate(properties, 1):
            meta = prop.get("metadata", {})
            title = meta.get("title", f"Property {prop.get('id')}")
            bhk = meta.get("bhk", "N/A")
            ptype = meta.get("property_type", "Property")
            loc = meta.get("location", "N/A")
            city = meta.get("city", "N/A")
            price = meta.get("price_lakh", "N/A")
            area = meta.get("area_sqft", "N/A")
            trans = meta.get("transaction_type", "buy")
            amenities = meta.get("amenities", "")
            avail = meta.get("availability", "")

            chunk = (
                f"Property {idx}: {title} ({bhk} BHK {ptype}) in {loc}, {city}.\n"
                f"  - Price: {price} Lakh INR | Area: {area} sqft | Type: {trans} | Status: {avail}\n"
                f"  - Amenities: {amenities}"
            )
            formatted_chunks.append(chunk)

        return "\n\n".join(formatted_chunks)
