import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
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
        "delhi": "Delhi",
        "ghaziabad": "Ghaziabad",
        "indirapuram": "Ghaziabad",
        "vaishali": "Ghaziabad",
        "vasundhara": "Ghaziabad",
        "raj nagar": "Ghaziabad",
        "crossings republik": "Ghaziabad",
        "kaushambi": "Ghaziabad",
        "lucknow": "Lucknow",
        "agra": "Agra",
        "meerut": "Meerut",
        "faridabad": "Faridabad",
        "jaipur": "Jaipur",
        "ahmedabad": "Ahmedabad",
        "surat": "Surat",
        "indore": "Indore",
        "bhopal": "Bhopal",
        "nagpur": "Nagpur",
        "chandigarh": "Chandigarh",
        # Delhi NCR popular localities
        "saket": "Delhi",
        "dwarka": "Delhi",
        "rohini": "Delhi",
        "vasant vihar": "Delhi",
        "hauz khas": "Delhi",
        "chattarpur": "Delhi",
        "greater kailash": "Delhi",
        "gk": "Delhi",
        "defence colony": "Delhi",
        "lajpat nagar": "Delhi",
        "kalkaji": "Delhi",
        "uttam nagar": "Delhi",
        "janakpuri": "Delhi",
        "karol bagh": "Delhi",
        "paschim vihar": "Delhi",
        "model town": "Delhi",
        "laxmi nagar": "Delhi",
        "pitampura": "Delhi",
        "mayur vihar": "Delhi",
        "safdarjung": "Delhi",
        "dlf": "Gurgaon",
        "sohna": "Gurgaon",
        "cyber city": "Gurgaon",
        "golf course": "Gurgaon",
        "sushant lok": "Gurgaon",
        "greater noida": "Noida",
        "yamuna expressway": "Noida",
        "pari chowk": "Noida",
    }

    PROPERTY_TYPES = {
        "apartment": "Apartment",
        "flat": "Apartment",
        "villa": "Villa",
        "penthouse": "Penthouse",
        "studio": "Studio Apartment",
        "studio apartment": "Studio Apartment",
        "independent floor": "Independent Floor",
        "builder floor": "Independent Floor",
        "independent house": "Independent House",
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
        - bhk (strict integer count)
        - property_type
        - transaction_type ('buy' or 'rent', defaulting to 'buy' if not specified)
        - is_default_transaction (True if defaulted to buy)
        - max_price (in Lakhs for buy, or in Thousands for rent)
        """
        if not text:
            return {
                "city": None,
                "bhk": None,
                "property_type": None,
                "transaction_type": "buy",
                "is_default_transaction": True,
                "max_price": None
            }

        lower_text = text.lower().strip()

        # 1. City extraction
        found_city = None
        for city_key, city_val in self.KNOWN_CITIES.items():
            if re.search(r'\b' + re.escape(city_key) + r'\b', lower_text):
                found_city = city_val
                break

        # 2. Strict BHK extraction (e.g. "2BHK", "2 BHK", "do bhk", "3 bedroom")
        found_bhk = None
        bhk_num_map = {
            "1": 1, "one": 1, "ek": 1,
            "2": 2, "two": 2, "do": 2,
            "3": 3, "three": 3, "teen": 3,
            "4": 4, "four": 4, "char": 4, "chaar": 4,
            "5": 5, "five": 5, "paanch": 5, "panch": 5
        }
        bhk_pattern = r'\b(1|2|3|4|5|one|two|three|four|five|ek|do|teen|char|chaar|paanch|panch)\s*(?:-| )*(?:bhk|bedroom|bed)\b'
        bhk_match = re.search(bhk_pattern, lower_text)
        if bhk_match:
            found_bhk = bhk_num_map.get(bhk_match.group(1).lower())

        # 3. Property Type extraction
        found_prop_type = None
        for ptype_key, ptype_val in self.PROPERTY_TYPES.items():
            if re.search(r'\b' + re.escape(ptype_key) + r'\b', lower_text):
                found_prop_type = ptype_val
                break

        # 4. Transaction Type extraction ('buy' vs 'rent')
        # If user does not say buy or rent, default to buy
        has_rent = bool(re.search(r'\b(rent|rental|lease|renting|kiraye|kiraya|bhaada|bhada)\b', lower_text))
        has_buy = bool(re.search(r'\b(buy|purchase|buying|sale|khareedna|kharidna|lena)\b', lower_text))

        if has_rent and not has_buy:
            found_trans_type = "rent"
            is_default_transaction = False
        elif has_buy and not has_rent:
            found_trans_type = "buy"
            is_default_transaction = False
        elif has_rent and has_buy:
            # Comparison query
            found_trans_type = None
            is_default_transaction = False
        else:
            # Default to buy listings
            found_trans_type = "buy"
            is_default_transaction = True

        # 5. Max Price extraction
        # "under 50 lakh" budget applies only to buy listings.
        # For rent, interpret budget like "under 40 thousand", "40k", "under 40000" as monthly rent.
        found_max_price = None
        if found_trans_type == "rent":
            # Check for thousand / k / hazar or explicit 4-6 digit monthly numbers
            rent_match = re.search(
                r'(?:under|below|budget|within|around|upto)?\s*(\d+(?:\.\d+)?)\s*(thousand|k|hazar|hazaron)\b',
                lower_text
            )
            raw_match = re.search(r'(?:under|below|budget|within|around|upto)\s*(\d{4,6})\b', lower_text)

            if raw_match:
                found_max_price = float(raw_match.group(1)) / 1000.0  # e.g. 40000 -> 40.0
            elif rent_match:
                found_max_price = float(rent_match.group(1))
        else:
            # For buy, extract in Lakhs or Crores
            price_match = re.search(
                r'(?:under|below|budget|within|around|upto)?\s*(\d+(?:\.\d+)?)\s*(lakhs?|lacs?|lac|crores?|cr|l)\b',
                lower_text
            )
            if price_match:
                val = float(price_match.group(1))
                unit = price_match.group(2)
                if unit in ["crore", "crores", "cr"]:
                    val = val * 100.0  # Convert Crore to Lakhs
                found_max_price = val

        return {
            "city": found_city,
            "bhk": found_bhk,
            "property_type": found_prop_type,
            "transaction_type": found_trans_type,
            "is_default_transaction": is_default_transaction,
            "max_price": found_max_price
        }

    def search(self, query: str, filters: Dict[str, Any] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Embeds query text and retrieves properties from ChromaDB with strict metadata filters.

        Requirements:
        1. Strict BHK filter: If user specified BHK, exact matches must have that BHK.
           If fewer than top_k match, closest alternatives in the same city are returned
           and explicitly marked with `is_alternative = True`.
        2. Rent vs Buy: If user is looking to buy, never return rent listings.
           If user is looking to rent, only return rent listings.
        3. If a city filter is supplied and no listings exist for that city,
           returns an empty list so the assistant can honestly say so.
        """
        if self.collection.count() == 0:
            return []

        query_embedding = self.model.encode(query).tolist()

        city_req = filters.get("city") if filters else None
        trans_req = filters.get("transaction_type") if filters else None
        bhk_req = filters.get("bhk") if filters else None
        prop_type_req = filters.get("property_type") if filters else None
        max_price_req = filters.get("max_price") if filters else None

        # ── 1. City existence check ───────────────────────────────────────────
        if city_req:
            try:
                city_check = self.collection.get(where={"city": {"$eq": city_req}}, limit=1)
                if not city_check or not city_check.get("ids") or len(city_check["ids"]) == 0:
                    return []
            except Exception:
                pass

        # ── 2. Query for Exact Matches ────────────────────────────────────────
        exact_where_conditions = []
        if city_req:
            exact_where_conditions.append({"city": {"$eq": city_req}})
        if trans_req:
            exact_where_conditions.append({"transaction_type": {"$eq": trans_req}})
        if bhk_req is not None:
            exact_where_conditions.append({"bhk": {"$eq": bhk_req}})
        if prop_type_req:
            exact_where_conditions.append({"property_type": {"$eq": prop_type_req}})
        if max_price_req is not None:
            exact_where_conditions.append({"price_lakh": {"$lte": max_price_req}})

        exact_where = None
        if len(exact_where_conditions) == 1:
            exact_where = exact_where_conditions[0]
        elif len(exact_where_conditions) > 1:
            exact_where = {"$and": exact_where_conditions}

        exact_results = None
        try:
            exact_results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=exact_where
            )
        except Exception:
            exact_results = None

        exact_properties = []
        if exact_results and exact_results.get("ids") and len(exact_results["ids"][0]) > 0:
            ids = exact_results["ids"][0]
            metas = exact_results["metadatas"][0] if exact_results.get("metadatas") else [{}] * len(ids)
            docs = exact_results["documents"][0] if exact_results.get("documents") else [""] * len(ids)
            dists = exact_results["distances"][0] if exact_results.get("distances") else [0.0] * len(ids)
            for i in range(len(ids)):
                dist = dists[i]
                sim_score = round(1.0 / (1.0 + dist), 4)
                exact_properties.append({
                    "id": ids[i],
                    "metadata": metas[i],
                    "document": docs[i],
                    "score": sim_score,
                    "is_alternative": False
                })

        # If we have enough exact matches, return them immediately
        if len(exact_properties) >= top_k:
            return exact_properties[:top_k]

        # ── 3. Find Closest Alternatives if fewer than top_k match ───────────
        # Never mix silently: alternative properties are marked with `is_alternative = True`.
        # Transaction type is strictly preserved (never mix buy and rent).
        alt_properties = []
        exact_ids = {p["id"] for p in exact_properties}

        alt_where_conditions = []
        if city_req:
            alt_where_conditions.append({"city": {"$eq": city_req}})
        if trans_req:
            alt_where_conditions.append({"transaction_type": {"$eq": trans_req}})

        alt_where = None
        if len(alt_where_conditions) == 1:
            alt_where = alt_where_conditions[0]
        elif len(alt_where_conditions) > 1:
            alt_where = {"$and": alt_where_conditions}

        try:
            needed = top_k + len(exact_ids)
            alt_results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=needed,
                where=alt_where
            )
            if alt_results and alt_results.get("ids") and len(alt_results["ids"][0]) > 0:
                ids = alt_results["ids"][0]
                metas = alt_results["metadatas"][0] if alt_results.get("metadatas") else [{}] * len(ids)
                docs = alt_results["documents"][0] if alt_results.get("documents") else [""] * len(ids)
                dists = alt_results["distances"][0] if alt_results.get("distances") else [0.0] * len(ids)
                for i in range(len(ids)):
                    if ids[i] in exact_ids:
                        continue
                    dist = dists[i]
                    sim_score = round(1.0 / (1.0 + dist), 4)
                    alt_properties.append({
                        "id": ids[i],
                        "metadata": metas[i],
                        "document": docs[i],
                        "score": sim_score,
                        "is_alternative": True
                    })
                    if len(exact_properties) + len(alt_properties) >= top_k:
                        break
        except Exception:
            pass

        return exact_properties + alt_properties

    def format_results_for_llm(self, properties: List[Dict[str, Any]], is_default_transaction: bool = False) -> str:
        """
        Formats retrieved properties into structured context for LLM prompt injection.
        Clearly separates exact matching properties from nearby / alternative options.
        Displays rent as monthly rupees (e.g. ₹35,000/month) and buy in Lakhs/Crore.
        """
        if not properties:
            return "No matching properties found in database."

        exact = [p for p in properties if not p.get("is_alternative")]
        alts = [p for p in properties if p.get("is_alternative")]

        formatted_chunks = []

        def _format_prop(prop: Dict[str, Any], idx: int) -> str:
            meta = prop.get("metadata", {})
            title = meta.get("title", f"Property {prop.get('id')}")
            bhk = meta.get("bhk", "N/A")
            ptype = meta.get("property_type", "Property")
            loc = meta.get("location", "N/A")
            city = meta.get("city", "N/A")
            price = meta.get("price_lakh", "N/A")
            area = meta.get("area_sqft", "N/A")
            trans = (meta.get("transaction_type") or "buy").lower()
            amenities = meta.get("amenities", "")
            avail = meta.get("availability", "")

            if trans == "rent":
                try:
                    price_display = f"₹{int(float(price) * 1000):,}/month"
                except Exception:
                    price_display = f"₹{price}/month"
            else:
                try:
                    p_val = float(price)
                    if p_val >= 100.0:
                        price_display = f"₹{p_val/100:.2f} Cr"
                    else:
                        price_display = f"₹{p_val:g} Lakh"
                except Exception:
                    price_display = f"₹{price} Lakh"

            return (
                f"Property {idx}: {title} ({bhk} BHK {ptype}) in {loc}, {city}.\n"
                f"  - Price: {price_display} | Area: {area} sqft | Type: {trans.capitalize()} | Status: {avail}\n"
                f"  - Amenities: {amenities}"
            )

        if exact:
            formatted_chunks.append("=== Exact Matching Properties ===")
            for idx, prop in enumerate(exact, 1):
                formatted_chunks.append(_format_prop(prop, idx))

        if alts:
            if exact:
                formatted_chunks.append("\n=== Nearby / Alternative Options (different BHK or budget in same city) ===")
            else:
                formatted_chunks.append("=== Nearby Options in this city (no exact match found) ===")
            for idx, prop in enumerate(alts, len(exact) + 1):
                formatted_chunks.append(_format_prop(prop, idx))

        if is_default_transaction:
            formatted_chunks.append("\n[Note: Defaulted to buy listings as per user preference. Rental options are also available in this area.]")

        return "\n\n".join(formatted_chunks)
