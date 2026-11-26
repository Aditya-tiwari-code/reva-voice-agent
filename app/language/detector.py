import re
from typing import List
from langdetect import detect_langs, DetectorFactory

# Set seed for reproducible langdetect results
DetectorFactory.seed = 0

class LanguageDetector:
    """
    Detects language (Hindi, English, Hinglish), intent, and prompt complexity
    for real estate voice agent queries.
    """

    HINGLISH_KEYWORDS = {
        "kitna", "kitne", "hai", "hain", "kya", "chahiye", "dekhna", "batao",
        "kahan", "paas", "sasta", "kam", "dono", "accha", "bhi", "me", "mein",
        "par", "ko", "se", "aur", "ye", "yeh", "wo", "woh", "hoga", "milega",
        "kab", "bhai", "ji", "sabse", "kaunsa", "karo", "liya", "wala", "wali",
        "namaste", "mujhe"
    }

    SIMPLE_INTENTS = {
        "price_inquiry",
        "availability_check",
        "location_query",
        "property_details",
        "site_visit_request",
        "greeting"
    }

    COMPLEX_INTENTS = {
        "negotiation",
        "comparison",
        "unknown"
    }

    def detect_language(self, text: str) -> str:
        """
        Determines if input text is 'hindi', 'english', or 'hinglish'.
        - Mixed script or Latin with Hinglish vocabulary / low confidence -> 'hinglish'
        - Devanagari script -> 'hindi'
        - Pure English -> 'english'
        """
        if not text or not text.strip():
            return "english"

        cleaned_text = text.strip()
        lower_text = cleaned_text.lower()

        has_devanagari = bool(re.search(r'[\u0900-\u097F]', cleaned_text))
        has_latin = bool(re.search(r'[a-zA-Z]', cleaned_text))

        # Rule 1: Mix of Devanagari and Latin script
        if has_devanagari and has_latin:
            return "hinglish"

        # Rule 2: Pure Devanagari script
        if has_devanagari and not has_latin:
            return "hindi"

        # Rule 3: Latin script - check for Hinglish keywords
        words = set(re.findall(r'\b\w+\b', lower_text))
        if words.intersection(self.HINGLISH_KEYWORDS):
            return "hinglish"

        # Rule 4: Use langdetect for confidence check
        try:
            predictions = detect_langs(cleaned_text)
            if predictions:
                top_pred = predictions[0]
                lang = top_pred.lang
                prob = top_pred.prob

                if prob < 0.8:
                    return "hinglish"

                if lang == "hi":
                    return "hinglish" if has_latin else "hindi"
                elif lang == "en":
                    return "english"
                else:
                    return "hinglish"
        except Exception:
            pass

        return "english" if has_latin else "hinglish"

    def detect_intent(self, text: str) -> str:
        """
        Classifies user query into one of 9 real estate intents:
        'price_inquiry', 'availability_check', 'location_query', 'property_details',
        'site_visit_request', 'negotiation', 'comparison', 'greeting', 'unknown'
        """
        if not text or not text.strip():
            return "unknown"

        lower_text = text.lower().strip()

        # Priority 1: Greeting (standalone short greetings)
        if re.search(r'\b(hi|hello|hey|namaste|namaskar|good morning|good evening)\b', lower_text):
            if len(lower_text.split()) <= 4 and not any(k in lower_text for k in ["bhk", "price", "location", "visit", "kitna"]):
                return "greeting"

        # Priority 2: Site Visit Request
        if re.search(r'\b(visit|dekhna|dekhne|site visit|book visit|tour|dekna|appointment|schedule visit|dekhna hai)\b', lower_text):
            return "site_visit_request"

        # Priority 3: Negotiation
        if re.search(r'\b(negotiate|discount|kam|sasta|best price|final price|kam karo|kam ho|bargain|budget kam)\b', lower_text):
            return "negotiation"

        # Priority 4: Comparison
        if re.search(r'\b(compare|comparison|versus|vs|difference|dono|dono me|better|behtar|kaunsa)\b', lower_text):
            return "comparison"

        # Priority 5: Property Details (check sqft, parking, amenities, details specifically before generic price/location)
        if re.search(r'\b(sqft|square feet|square foot|parking|amenities|details|jankari|dimensions|features|floor)\b', lower_text):
            has_price_keyword = bool(re.search(r'\b(price|cost|rate|daam|lakh|crore|cr|budget|pricing)\b', lower_text))
            if not has_price_keyword:
                return "property_details"

        # Priority 6: Availability Check
        if re.search(r'\b(available|khali|ready to move|possession|vacant|kab milega|is it free|availability)\b', lower_text):
            return "availability_check"

        # Priority 7: Price Inquiry
        if re.search(r'\b(price|cost|rate|kitna|kitne|daam|budget|lakh|crore|cr|pricing)\b', lower_text):
            return "price_inquiry"

        # Priority 8: Location Query
        if re.search(r'\b(where|location|kahan|address|area|near|paas|locality|which place)\b', lower_text):
            return "location_query"

        # Priority 9: Property Details (general fallback for bhk, flat, apartment, house, villa)
        if re.search(r'\b(bhk|batao|flat|apartment|house|villa)\b', lower_text):
            return "property_details"

        # Fallback greeting
        if re.search(r'\b(hi|hello|hey|namaste|namaskar)\b', lower_text):
            return "greeting"

        return "unknown"

    def estimate_complexity(self, text: str, intent: str) -> str:
        """
        Estimates query complexity ('simple' or 'complex') to guide model routing.
        - Simple: Standard queries (price, availability, location, details, greeting) with short/moderate length.
        - Complex: Negotiation, comparison, unknown intents, or long multi-part queries.
        """
        if intent in self.COMPLEX_INTENTS:
            return "complex"

        word_count = len(text.strip().split())
        if word_count > 18:
            return "complex"

        if intent in self.SIMPLE_INTENTS:
            return "simple"

        return "complex"
