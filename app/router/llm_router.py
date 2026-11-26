import os
import sys
import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("reva.router")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def build_spoken_text(
    reply_text: str,
    language: str = "hinglish",
    properties: Optional[List[Dict[str, Any]]] = None,
    intent: str = "property_inquiry",
    city_asked: Optional[str] = None
) -> str:
    """
    Constructs a short, natural spoken line (max 2-3 sentences) suitable for audio TTS playback.
    Rules:
    - Never read out bullet lists or long property specs.
    - Summarize matches ('I found 3 options...').
    - End with ONE clear question or next step.
    - For Hindi, write in Devanagari.
    - For Hinglish, write in natural Devanagari Hindi with simple common English words
      so that gTTS (lang='hi') pronounces it with natural Indian phonetics.
    - For English, write in fluent, warm conversational English.
    """
    lang = (language or "hinglish").lower().strip()
    if lang in ["hi", "hindi"]:
        norm_lang = "hindi"
    elif lang in ["en", "english"]:
        norm_lang = "english"
    else:
        norm_lang = "hinglish"

    prop_count = len(properties) if properties else 0
    first_prop_city = ""
    first_prop_bhk = ""
    if properties and len(properties) > 0:
        meta = properties[0].get("metadata") or {}
        first_prop_city = meta.get("city") or ""
        bhk_val = meta.get("bhk")
        if bhk_val:
            first_prop_bhk = f"{bhk_val}BHK "

    # 1. Greeting
    if intent == "greeting":
        if norm_lang == "hindi":
            return "नमस्ते! मैं REVA हूँ, आपकी रियल एस्टेट AI असिस्टेंट। आप किस शहर या बजट में प्रॉपर्टी देख रहे हैं?"
        elif norm_lang == "english":
            return "Hello! I am REVA, your real estate AI assistant. What city, BHK, or budget are you looking for?"
        else: # Hinglish
            return "नमस्ते! मैं REVA हूँ, आपकी रियल एस्टेट असिस्टेंट। आप किस शहर या बजट में फ्लैट ढूँढ रहे हैं?"

    # 2. Site Visit Request
    if intent == "site_visit_request":
        if norm_lang == "hindi":
            return "जी बिल्कुल! मैं आपके लिए साइट विज़िट शेड्यूल कर सकती हूँ। क्या आप कल सुबह या शाम का समय पसंद करेंगे?"
        elif norm_lang == "english":
            return "Sure! I would be happy to schedule a site visit for you. Would you prefer a morning or evening slot tomorrow?"
        else:
            return "जी बिल्कुल! मैं आपके लिए साइट विज़िट प्लान कर सकती हूँ। क्या आप कल सुबह का टाइम प्रिफर करेंगे या शाम का?"

    # 3. Negotiation
    if intent == "negotiation":
        if norm_lang == "hindi":
            return "जी हाँ, बातचीत की गुंजाइश ज़रूर है। मैं हमारे सीनियर मैनेजर से आपकी बात करवा सकती हूँ, क्या आप साइट विज़िट के लिए तैयार हैं?"
        elif norm_lang == "english":
            return "Yes, there is definitely room for price discussion. I can connect you with our senior property manager. Would you like to schedule a visit first?"
        else:
            return "जी हाँ, प्राइस पर नेगोशिएशन बिल्कुल पॉसिबल है। मैं हमारे सीनियर मैनेजर से बात करवा सकती हूँ, क्या आप पहले साइट विज़िट देखना चाहेंगे?"

    # 4. Comparison
    if intent == "comparison":
        if norm_lang == "hindi":
            return "दोनों ही लोकेशन्स के अपने फायदे हैं। मैंने नीचे तुलना दी है, क्या आप इनमें से किसी को विज़िट करना चाहेंगे?"
        elif norm_lang == "english":
            return "Both locations have unique advantages. Check out the comparison below, and let me know if you would like to visit either."
        else:
            return "दोनों लोकेशन्स के अपने फायदे हैं। नीचे दिए ऑप्शन्स देखें, और बताइए आप किस प्रोजेक्ट की विज़िट करना चाहेंगे?"

    # 5. Property search results available
    if prop_count > 0:
        loc_str = first_prop_city or "आपके पसंदीदा एरिया"
        loc_en = first_prop_city or "your preferred area"
        if norm_lang == "hindi":
            return f"नमस्ते! मुझे {loc_str} में {prop_count} बेहतरीन {first_prop_bhk}विकल्प मिले हैं। नीचे दिए विकल्पों को देखें और बताएं कि आप कब विज़िट करना चाहेंगे।"
        elif norm_lang == "english":
            return f"I found {prop_count} verified {first_prop_bhk}options in {loc_en}. Have a look at them below, and let me know when you'd like to visit."
        else: # Hinglish in Devanagari for natural Indian TTS pronunciation
            return f"मैंने {loc_str} में {first_prop_bhk}के {prop_count} बढ़िया ऑप्शन्स ढूँढे हैं। आप नीचे देख सकते हैं, क्या आप साइट विज़िट प्लान करना चाहेंगे?"

    # 6. No matching properties (honest statement)
    if city_asked:
        if norm_lang == "hindi":
            return f"माफ़ करें, {city_asked} में अभी कोई मैचिंग लिस्टिंग उपलब्ध नहीं है, लेकिन नजदीकी नोएडा में बेहतरीन विकल्प हैं। क्या मैं नोएडा के विकल्प दिखाऊं?"
        elif norm_lang == "english":
            return f"Sorry, I couldn't find an exact match in {city_asked}, but I have great options in nearby Noida. Would you like to check them?"
        else:
            return f"माफ़ करें, {city_asked} में अभी कोई डायरेक्ट लिस्टिंग नहीं मिली, लेकिन पास के नोएडा में अच्छे ऑप्शन्स हैं। क्या मैं वो दिखाऊं?"

    # 7. General fallback
    if norm_lang == "hindi":
        return "मुझे आपकी ज़रूरत समझ आ गई है। कृपया अपना पसंदीदा एरिया, बजट या बीएचके बताएं ताकि मैं सही विकल्प दिखा सकूँ।"
    elif norm_lang == "english":
        return "Got it! Please share your preferred city, budget, or BHK configuration so I can find the best verified properties for you."
    else:
        return "मुझे आपकी रिक्वायरमेंट समझ आ गई। कृपया अपनी पसंदीदा लोकेशन, बजट या बीएचके बताइए ताकि मैं बेस्ट ऑप्शन्स दिखा सकूँ।"


def parse_structured_llm_response(
    raw_text: str,
    default_language: str = "hinglish",
    default_intent: str = "property_inquiry",
    properties: Optional[List[Dict[str, Any]]] = None,
    user_text: str = "",
    extracted_filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Safely parses LLM output into the Phase 1 structured JSON schema:
    {
        "reply_text": str,
        "spoken_text": str,
        "language": "en | hi | hinglish",
        "intent": str,
        "slots": {bhk, city, budget, buy_or_rent, timeline},
        "next_action": "ask_slot | show_properties | schedule_visit | handoff"
    }
    Falls back gracefully to plain text + synthesized spoken line if output is not valid JSON.
    """
    filters = extracted_filters or {}
    slots_base = {
        "bhk": filters.get("bhk"),
        "city": filters.get("city"),
        "budget": filters.get("max_price"),
        "buy_or_rent": filters.get("transaction_type") or "buy",
        "timeline": None
    }

    prop_count = len(properties) if properties else 0
    default_next_action = "show_properties" if prop_count > 0 else (
        "schedule_visit" if default_intent == "site_visit_request" else (
            "handoff" if default_intent == "negotiation" else "ask_slot"
        )
    )

    clean_raw = (raw_text or "").strip()
    parsed_json = None

    # Try extracting JSON object from markdown fences or bare braces
    json_candidate = clean_raw
    json_fence_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', clean_raw, re.DOTALL)
    if json_fence_match:
        json_candidate = json_fence_match.group(1).strip()
    else:
        brace_match = re.search(r'(\{[\s\S]*\})', clean_raw)
        if brace_match:
            json_candidate = brace_match.group(1).strip()

    try:
        import json as _json
        obj = _json.loads(json_candidate)
        if isinstance(obj, dict) and "reply_text" in obj:
            parsed_json = obj
    except Exception:
        parsed_json = None

    if parsed_json:
        reply_text = str(parsed_json.get("reply_text") or "").strip()
        spoken_text = str(parsed_json.get("spoken_text") or "").strip()
        lang = str(parsed_json.get("language") or default_language).lower().strip()
        if lang not in ["en", "hi", "hinglish", "english", "hindi"]:
            lang = default_language
        intent = str(parsed_json.get("intent") or default_intent)
        slots = parsed_json.get("slots")
        if not isinstance(slots, dict):
            slots = slots_base
        else:
            # Merge with extracted filters
            for k, v in slots_base.items():
                if slots.get(k) is None and v is not None:
                    slots[k] = v

        next_action = str(parsed_json.get("next_action") or default_next_action)
        if next_action not in ["ask_slot", "show_properties", "schedule_visit", "handoff"]:
            next_action = default_next_action

        # If spoken_text is empty or too long (>3 sentences or includes bullet points), rebuild cleanly
        if not spoken_text or "•" in spoken_text or spoken_text.count(".") + spoken_text.count("?") + spoken_text.count("।") > 3:
            spoken_text = build_spoken_text(reply_text, lang, properties, intent)

        return {
            "reply_text": reply_text or clean_raw,
            "spoken_text": spoken_text,
            "language": lang,
            "intent": intent,
            "slots": slots,
            "next_action": next_action
        }

    # Fallback when raw LLM response is plain text
    fallback_spoken = build_spoken_text(
        reply_text=clean_raw,
        language=default_language,
        properties=properties,
        intent=default_intent
    )

    return {
        "reply_text": clean_raw,
        "spoken_text": fallback_spoken,
        "language": default_language,
        "intent": default_intent,
        "slots": slots_base,
        "next_action": default_next_action
    }


def generate_natural_conversation(
    user_text: str,
    context: str = "",
    properties: Optional[List[Dict[str, Any]]] = None,
    language: str = "hinglish",
    intent: str = "property_inquiry",
    is_default_transaction: bool = False
) -> str:
    """
    Synthesizes a fluent, natural conversational response in Hindi/Hinglish/English
    using extracted property details, avoiding robotic template strings.
    Strictly separates exact BHK matches from nearby alternative options.
    Displays rent as monthly rupees (e.g. ₹35,000/month) and buy in Lakhs/Crore.
    """
    lang = (language or "hinglish").lower()
    user_lower = (user_text or "").lower()

    # 1. Format matching properties as clean bullet points.
    # Group into exact matches vs nearby/alternative options.
    exact_items = []
    alt_items = []
    if properties:
        for p in properties[:3]:
            meta = p.get("metadata") or {}
            title = meta.get("title") or "Verified Property"
            loc = meta.get("location") or ""
            city = meta.get("city") or ""
            loc_str = f" ({loc}, {city})" if (loc or city) else ""
            bhk = meta.get("bhk")
            bhk_str = f"{bhk} BHK " if bhk else ""
            ptype = meta.get("property_type") or "Apartment"
            trans = (meta.get("transaction_type") or "").lower()
            price = meta.get("price_lakh")

            if trans == "rent":
                try:
                    price_str = f"₹{int(float(price) * 1000):,}/month"
                except Exception:
                    price_str = f"₹{price}/month"
            else:
                try:
                    p_val = float(price)
                    if p_val >= 100.0:
                        price_str = f"₹{p_val/100:.2f} Cr"
                    else:
                        price_str = f"₹{p_val:g} Lakh"
                except Exception:
                    price_str = f"₹{price} Lakh" if price else ""

            area = meta.get("area_sqft")
            area_str = f" | {area} sqft" if area else ""
            trans_str = f" | {trans.capitalize()}" if trans else ""
            avail = meta.get("availability") or "Ready to Move"

            bullet = f"• {title}{loc_str} — {bhk_str}{ptype} | {price_str}{area_str}{trans_str} | {avail}"
            if p.get("is_alternative"):
                alt_items.append(bullet)
            else:
                exact_items.append(bullet)
    elif context and "Property" in context:
        for block in context.split("[Property"):
            if not block.strip():
                continue
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            first_line = lines[0].strip("]: ") if lines else ""
            city_match = re.search(r'City:\s*([^,\n]+)', block)
            price_match = re.search(r'Price:\s*([^,\n]+)', block)
            city_str = city_match.group(1).strip() if city_match else ""
            price_str = price_match.group(1).strip() if price_match else ""
            if first_line:
                exact_items.append(f"• {first_line} ({city_str}) — {price_str}".strip(" — ()"))

    if exact_items and alt_items:
        bullets_text = (
            "\n".join(exact_items) +
            "\n\nNearby options in the same city:\n" +
            "\n".join(alt_items)
        )
    elif exact_items:
        bullets_text = "\n".join(exact_items)
    elif alt_items:
        bullets_text = "Nearby options in the same city:\n" + "\n".join(alt_items)
    else:
        bullets_text = ""

    rent_note = ""
    if is_default_transaction and bullets_text:
        if lang == "hindi":
            rent_note = "\n\n(नोट: यदि आप किराए पर देखना चाहते हैं, तो इस क्षेत्र में किराए के विकल्प भी उपलब्ध हैं।)"
        elif lang == "english":
            rent_note = "\n\n(Note: Rental options are also available in this area if you're looking to rent.)"
        else:
            rent_note = "\n\n(Note: Agar aap rent par dekhna chahte hain, toh is area mein rental options bhi available hain.)"

    # 2. Contextual Natural Dialogue Generation
    if intent == "greeting" or any(w in user_lower for w in ["hi", "hello", "hey", "namaste", "namaskar"]):
        if lang == "hindi":
            return "नमस्ते! मैं REVA हूँ, आपकी रियल एस्टेट AI असिस्टेंट। मैं नोएडा, गुड़गांव, बैंगलोर और अन्य शहरों में आपके बजट के अनुसार बेहतरीन प्रॉपर्टी खोजने में आपकी मदद कर सकती हूँ। आप किस एरिया या बजट में फ्लैट देख रहे हैं?"
        elif lang == "english":
            return "Hello! I am REVA, your real estate AI assistant. I can help you find verified properties across Noida, Gurgaon, Bangalore, and other top cities. What location or budget are you looking for?"
        else:
            return "Namaste! Main REVA hoon, aapki real estate AI assistant. Main Noida, Gurgaon, Bangalore aur anya shahron mein aapke budget aur requirement ke mutabiq best properties khojne mein madad kar sakti hoon. Aap kis location ya kitne BHK ka flat dekh rahe hain?"

    if intent == "site_visit_request" or "visit" in user_lower or "dekhna" in user_lower:
        if bullets_text:
            return (
                f"Ji bilkul! Hum aapke liye site visit zaroor schedule kar denge. Hamare matching options hain:\n\n"
                f"{bullets_text}{rent_note}\n\n"
                "Kya aap kal subah ya shaam ka time prefer karenge? Hamari team aapse details confirm karne ke liye turant connect karegi."
            )
        return "Ji bilkul! Main aapke liye site visit zaroor schedule karwa deta hoon. Kya aap kal ka time prefer karenge ya weekend pe visit karna chahenge?"

    if intent == "negotiation" or "negotiate" in user_lower or "kam" in user_lower or "discount" in user_lower:
        if bullets_text:
            return (
                f"Ji haan, builder aur property owner se pricing par 3% se 5% tak negotiation ho sakti hai, khaaskar agar payment terms flexible hon.\n\n"
                f"{bullets_text}{rent_note}\n\n"
                "Main aapki baat hamare senior relationship manager se arrange karwa deta hoon jo aapko best deal dilwayenge."
            )
        return "Ji haan, property price par negotiation possible hai. Main aapki baat hamare senior property manager se connect karwa deta hoon jo aapko best possible discount negotiate karwa denge."

    if intent == "comparison" or "compare" in user_lower or "vs" in user_lower:
        if bullets_text:
            return (
                f"Dono hi locations ki apni khasiyat hai. Hamare paas available top matching options ye hain:\n\n"
                f"{bullets_text}{rent_note}\n\n"
                "Noida Expressway par planned infrastructure aur budget-friendly spacious flats milte hain, jabki Gurgaon business hubs aur premium social life ke liye popular hai. Aap investment ke liye dekh rahe hain ya personal use ke liye?"
            )
        return "Noida aur Gurgaon dono ke apne advantages hain. Noida planned road connectivity aur affordable options deta hai, jabki Gurgaon premium commercial connectivity provide karta hai. Aap investment ke liye dekh rahe hain ya self-use ke liye?"

    if intent in ("property_details", "sqft") or any(w in user_lower for w in ["sqft", "parking", "amenities", "details"]):
        if bullets_text:
            return (
                f"Is property mein covered car parking, 24/7 power backup, security aur modern clubhouse amenities uplabdh hain:\n\n"
                f"{bullets_text}{rent_note}\n\n"
                "Kya aap iska detailed floor plan ya brochure dekhna chahenge?"
            )

    # General Search / Price Inquiry
    if bullets_text:
        if lang == "hindi":
            return (
                f"नमस्ते! आपके सर्च के अनुसार हमारे पास ये बेहतरीन प्रॉपर्टीज उपलब्ध हैं:\n\n"
                f"{bullets_text}{rent_note}\n\n"
                "क्या आप इनमें से किसी प्रॉपर्टी की साइट विजिट बुक करना चाहेंगे या अधिक जानकारी चाहते हैं?"
            )
        elif lang == "english":
            return (
                f"Hello! Based on your requirement, here are the top verified matching properties:\n\n"
                f"{bullets_text}{rent_note}\n\n"
                "Would you like to schedule a site visit or view the detailed brochure for any of these?"
            )
        else:
            return (
                f"Namaste! Aapke search ke anusaar hamare paas ye matching verified properties available hain:\n\n"
                f"{bullets_text}{rent_note}\n\n"
                "Kya aap inme se kisi property ki site visit schedule karna chahenge ya pricing details janna chahenge?"
            )

    # Friendly fallback when no direct listing matched
    # Try to detect the city the user asked for so we can be honest
    import re as _re
    city_asked = None
    for _cw in ["ghaziabad", "delhi", "agra", "meerut", "faridabad", "lucknow",
                "jaipur", "ahmedabad", "surat", "indore", "bhopal", "nagpur"]:
        if _cw in user_lower:
            city_asked = _cw.capitalize()
            break

    if city_asked:
        if lang == "hindi":
            return (
                f"माफ़ करें, हमारे पास अभी {city_asked} में कोई लिस्टिंग उपलब्ध नहीं है। "
                "लेकिन नजदीकी नोएडा में हमारे पास कई बेहतरीन विकल्प हैं जैसे Godrej Woods (Sector 43, ₹110 Lakh) "
                "और ATS One Hamlet (Sector 104, ₹160 Lakh)। क्या मैं नोएडा के विकल्प दिखाऊं?"
            )
        return (
            f"Sorry, we currently don't have any listings in {city_asked}. "
            "However, we have great options in nearby Noida — for example Godrej Woods (Sector 43) at ₹110 Lakh "
            "and ATS One Hamlet (Sector 104) at ₹160 Lakh. "
            "Would you like me to show you more Noida properties in your budget?"
        )

    if lang == "hindi":
        return "नमस्ते! मुझे आपकी रिक्वायरमेंट समझ आ गई है। इस बजट और लोकेशन में नई यूनिट्स जल्द उपलब्ध होंगी। क्या आप नजदीकी सेक्टर में विकल्प देखना चाहेंगे?"
    return "Namaste! Mujhe aapki requirement samajh aa gayi hai. Is budget aur location mein kuch nayi properties shortlist ho rahi hain. Main aapko nearby sectors mein best verified options dikha sakta hoon. Kya aap koi specific sector prefer karenge?"


class AdaptiveLLMRouter:
    """
    Cost-Aware Dynamic LLM Router.
    Routes simple queries to Groq Llama 3 (fast, low-cost) and
    complex queries to Gemini 1.5 Flash.
    Provides robust fallback from Groq to Gemini and natural conversational fallback.
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        groq_model: Optional[str] = None,
        gemini_model: Optional[str] = None
    ):
        self._groq_api_key = groq_api_key
        self._gemini_api_key = gemini_api_key
        self._groq_model = groq_model
        self._gemini_model = gemini_model

        self._groq_client = None
        self._gemini_client_initialized = False

    @property
    def groq_api_key(self) -> str:
        if self._groq_api_key:
            return self._groq_api_key.strip().strip('"').strip("'")
        return settings.GROQ_API_KEY

    @property
    def gemini_api_key(self) -> str:
        if self._gemini_api_key:
            return self._gemini_api_key.strip().strip('"').strip("'")
        return settings.GEMINI_API_KEY

    @property
    def groq_model(self) -> str:
        return self._groq_model or settings.GROQ_MODEL or "qwen/qwen3.8-27b"

    @property
    def gemini_model(self) -> str:
        return self._gemini_model or settings.GEMINI_MODEL or "gemini-flash-lite-latest"

    @property
    def groq_client(self):
        if self._groq_client is not None:
            return self._groq_client

        key = self.groq_api_key
        if key and key.strip():
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=key)
            except Exception as e:
                print(f"[GROQ CLIENT INIT ERROR] Failed to instantiate Groq client: {e}")
                logger.error(f"Failed to instantiate Groq client: {e}")
                self._groq_client = None
        return self._groq_client

    def _init_gemini(self):
        if not self._gemini_client_initialized:
            key = self.gemini_api_key
            if key and key.strip():
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=key, transport="rest")
                    self._gemini_client_initialized = True
                except Exception as e:
                    print(f"[GEMINI INIT ERROR] Failed to configure Gemini: {e}")
                    logger.error(f"Failed to configure Gemini: {e}")

    def calculate_cost(self, model_used: str, tokens: int) -> float:
        """
        Calculates estimated cost in USD based on model token usage.
        - Groq Llama 3: ~$0.00008 per 1,000 tokens
        - Gemini Flash: ~$0.00015 per 1,000 tokens
        """
        if tokens <= 0:
            return 0.0

        if "groq" in model_used.lower() or "llama" in model_used.lower():
            rate_per_1k = 0.00008
        else:
            rate_per_1k = 0.00015

        return round((tokens / 1000.0) * rate_per_1k, 6)

    def _call_groq(self, text: str, system_prompt: str) -> Tuple[Optional[str], int, Optional[str]]:
        """
        Calls Groq Llama 3 API.
        Returns: (response_text, tokens_used, error_message)
        """
        client = self.groq_client
        if not client:
            groq_key = self.groq_api_key
            err = f"GROQ_API_KEY is not configured in .env ('{groq_key or 'EMPTY'}'). Please update .env with a valid key starting with 'gsk_' from console.groq.com."
            print(f"\n[GROQ WARNING] {err}")
            logger.warning(err)
            return None, 0, err

        try:
            completion = client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=300
            )
            response_text = completion.choices[0].message.content
            tokens_used = (
                completion.usage.total_tokens
                if hasattr(completion, "usage") and completion.usage
                else len((system_prompt + text + response_text).split())
            )
            return response_text, tokens_used, None

        except Exception as e:
            # 1. SHOW THE ACTUAL ERROR WHEN GROQ API FAILS
            error_type = type(e).__name__
            error_msg = str(e)
            error_details = f"{error_type}: {error_msg}"

            print("\n" + "=" * 65)
            print("[GROQ API ERROR] Groq API call failed!")
            print(f"   Error Type   : {error_type}")
            print(f"   Error Message: {error_msg}")
            if hasattr(e, "status_code"):
                print(f"   HTTP Status  : {getattr(e, 'status_code')}")
            if hasattr(e, "response"):
                print(f"   Response Body: {getattr(e, 'response')}")
            print("=" * 65 + "\n")

            logger.error(f"[GROQ API ERROR] {error_details}", exc_info=True)
            return None, 0, error_details

    def _call_gemini(self, text: str, system_prompt: str) -> Tuple[Optional[str], int, Optional[str]]:
        """
        Calls Gemini 1.5 Flash API.
        Returns: (response_text, tokens_used, error_message)
        """
        gemini_key = self.gemini_api_key
        if not gemini_key or not gemini_key.strip():
            err = f"GEMINI_API_KEY is not configured in .env ('{gemini_key or 'EMPTY'}'). Please update .env with a valid key from aistudio.google.com."
            print(f"\n[GEMINI WARNING] {err}")
            logger.warning(err)
            return None, 0, err

        try:
            self._init_gemini()
            import google.generativeai as genai
            model = genai.GenerativeModel(
                model_name=self.gemini_model,
                system_instruction=system_prompt
            )
            response = model.generate_content(text)
            response_text = response.text
            tokens_used = (
                response.usage_metadata.total_token_count
                if hasattr(response, "usage_metadata") and response.usage_metadata
                else len((system_prompt + text + response_text).split())
            )
            return response_text, tokens_used, None

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            error_details = f"{error_type}: {error_msg}"

            print("\n" + "=" * 65)
            print("[GEMINI API ERROR] Gemini generate_content call failed!")
            print(f"   Error Type   : {error_type}")
            print(f"   Error Message: {error_msg}")
            print("=" * 65 + "\n")

            logger.error(f"[GEMINI API ERROR] {error_details}", exc_info=True)
            return None, 0, error_details

    def route(
        self,
        text: str,
        complexity: str = "simple",
        context: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        language: str = "hinglish",
        intent: str = "property_inquiry",
        properties: Optional[List[Dict[str, Any]]] = None,
        is_default_transaction: bool = False,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Routes prompt to Groq or Gemini based on complexity, enforcing Phase 1 structured JSON replies:
        - Simple queries route to Groq Llama 3 first.
        - If Groq fails, properly falls back to Gemini 1.5 Flash.
        - Complex queries route directly to Gemini 1.5 Flash (with Groq fallback).
        - If both remote LLMs fail, generates natural conversational Hindi/Hinglish response.
        - Parses output into structured schema: reply_text, spoken_text, language, intent, slots, next_action.
        """
        history_str = str(history) if history else "[]"
        system_prompt = (
            "You are REVA, a friendly and professional multilingual real estate AI assistant in India. "
            "You help customers find and evaluate properties.\n\n"
            "OUTPUT FORMAT INSTRUCTION:\n"
            "You MUST respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            "  \"reply_text\": \"full formatted text shown in the chat UI\",\n"
            "  \"spoken_text\": \"short natural 1-2 sentence line to be spoken aloud. NEVER read out bullet lists or prices of each listing. Summarize and end with ONE clear question or next step. For Hindi or Hinglish, write in Devanagari script for accurate speech synthesis.\",\n"
            "  \"language\": \"en | hi | hinglish\",\n"
            "  \"intent\": \"property_inquiry | site_visit_request | price_inquiry | negotiation | comparison | greeting | unknown\",\n"
            "  \"slots\": {\"bhk\": null, \"city\": null, \"budget\": null, \"buy_or_rent\": null, \"timeline\": null},\n"
            "  \"next_action\": \"ask_slot | show_properties | schedule_visit | handoff\"\n"
            "}\n\n"
            "Key guidelines:\n"
            "1. Always respond in the EXACT same language and tone the customer used (Hindi, English, or conversational Hinglish).\n"
            "2. Never say 'As an AI' or 'Fallback response'. Talk naturally like an experienced local real estate advisor.\n"
            "3. Use the provided property context accurately to answer pricing, location, BHK, and amenities.\n"
            "4. STRICT BHK AND TRANSACTION RULES:\n"
            "   - Only present properties that strictly match the user's requested BHK count.\n"
            "   - If fewer than 3 properties match and 'Nearby / Alternative Options' are provided in the context, introduce them clearly under 'Nearby options' (mentioning their different BHK) only after showing the exact matches. Never mix them silently.\n"
            "   - Display rent in monthly format (e.g. ₹35,000/month) and buy in Lakh or Crore (e.g. ₹42 Lakh or ₹1.5 Cr).\n"
            "   - Never show rent properties when the user asks to buy, and never show buy properties when the user asks to rent.\n"
            "   - If the user did not specify buy or rent, show buy listings and briefly mention that rental options are also available in this area.\n"
            "5. Keep answers concise, helpful, and invite the customer to book a site visit or ask follow-up questions.\n"
            f"Available properties context:\n{context}\n"
            f"Conversation history: {history_str}"
        )

        start_time = time.time()
        raw_output = ""
        tokens_used = 0
        model_used_label = "groq_llama3" if complexity == "simple" else "gemini_flash"
        groq_error = None
        gemini_error = None
        is_fallback = False

        if complexity == "simple":
            # 1. Attempt Groq Llama 3
            groq_resp, groq_tokens, groq_err = self._call_groq(text, system_prompt)

            if groq_resp:
                raw_output = groq_resp
                tokens_used = groq_tokens
                model_used_label = "groq_llama3"
            else:
                groq_error = groq_err
                # Fallback to Gemini
                print("[ROUTER FALLBACK] Groq API failed. Falling back to Gemini 1.5 Flash...")
                logger.info("[ROUTER FALLBACK] Groq API failed. Falling back to Gemini 1.5 Flash...")
                is_fallback = True

                gemini_resp, gemini_tokens, gemini_err = self._call_gemini(text, system_prompt)
                if gemini_resp:
                    raw_output = gemini_resp
                    tokens_used = gemini_tokens
                    model_used_label = "gemini_flash"
                else:
                    gemini_error = gemini_err
                    # Natural conversational response
                    raw_output = generate_natural_conversation(
                        user_text=text,
                        context=context,
                        properties=properties,
                        language=language,
                        intent=intent,
                        is_default_transaction=is_default_transaction
                    )
                    tokens_used = len((system_prompt + text + raw_output).split())
                    model_used_label = "groq_llama3"

        else:
            # Complex query: Attempt Gemini Flash first
            gemini_resp, gemini_tokens, gemini_err = self._call_gemini(text, system_prompt)

            if gemini_resp:
                raw_output = gemini_resp
                tokens_used = gemini_tokens
                model_used_label = "gemini_flash"
            else:
                gemini_error = gemini_err
                print("[ROUTER FALLBACK] Gemini API failed for complex query. Falling back to Groq Llama 3...")
                logger.info("[ROUTER FALLBACK] Gemini failed. Falling back to Groq...")
                is_fallback = True

                groq_resp, groq_tokens, groq_err = self._call_groq(text, system_prompt)
                if groq_resp:
                    raw_output = groq_resp
                    tokens_used = groq_tokens
                    model_used_label = "groq_llama3"
                else:
                    groq_error = groq_err
                    # Natural conversational response
                    raw_output = generate_natural_conversation(
                        user_text=text,
                        context=context,
                        properties=properties,
                        language=language,
                        intent=intent,
                        is_default_transaction=is_default_transaction
                    )
                    tokens_used = len((system_prompt + text + raw_output).split())
                    model_used_label = "gemini_flash"

        latency_ms = round((time.time() - start_time) * 1000.0, 2)
        estimated_cost = self.calculate_cost(model_used_label, tokens_used)

        # Parse structured JSON safely with graceful fallback
        parsed_result = parse_structured_llm_response(
            raw_text=raw_output,
            default_language=language,
            default_intent=intent,
            properties=properties,
            user_text=text,
            extracted_filters=filters
        )

        reply_text = parsed_result["reply_text"].strip()
        spoken_text = parsed_result["spoken_text"].strip()

        return {
            "response_text": reply_text,
            "reply_text": reply_text,
            "spoken_text": spoken_text,
            "language": parsed_result["language"],
            "intent": parsed_result["intent"],
            "slots": parsed_result["slots"],
            "next_action": parsed_result["next_action"],
            "structured": parsed_result,
            "model_used": model_used_label,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "estimated_cost_usd": estimated_cost,
            "is_fallback": is_fallback,
            "groq_error": groq_error,
            "gemini_error": gemini_error
        }
