import re
from typing import Dict, Any, List
from app.stt.transcriber import HinglishTranscriber
from app.language.detector import LanguageDetector
from app.rag.retriever import PropertyRetriever
from app.router.llm_router import AdaptiveLLMRouter
from app.tts.synthesizer import MultilingualSynthesizer

class ConversationAgent:
    """
    Core conversation agent integrating Speech, Language/Intent detection,
    RAG property search, Dynamic LLM routing, Lead Scoring, and Human Escalation logic.
    """

    TIMELINE_KEYWORDS = [
        "jaldi", "next month", "asap", "immediate", "ready to move",
        "this week", "urgent", "soon", "this month"
    ]

    ESCALATION_KEYWORDS = [
        "manager", "senior", "human", "real person",
        "banda chahiye", "aadmi se baat", "executive", "agent se baat",
        "speak to human", "talk to representative"
    ]

    def __init__(self):
        self.transcriber = HinglishTranscriber()
        self.detector = LanguageDetector()
        self.retriever = PropertyRetriever()
        self.router = AdaptiveLLMRouter()
        self.synthesizer = MultilingualSynthesizer()
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}

    def get_lead_score(self, session_data: Dict[str, Any]) -> int:
        """
        Calculates a lead qualification score from 0 to 100:
        +20 if budget mentioned
        +20 if location mentioned
        +20 if property_type mentioned
        +20 if timeline mentioned ("jaldi", "next month", "ASAP", etc.)
        +20 if site_visit_request intent detected
        """
        score = 0
        user_text = (session_data.get("user_text") or "").lower()
        filters = session_data.get("filters_extracted") or {}
        intent = session_data.get("intent") or ""

        # 1. Budget (+20)
        has_budget_filter = filters.get("max_price") is not None
        has_budget_text = bool(re.search(r'\b(budget|lakh|crore|cr|price|cost|rate|lacs)\b', user_text))
        if has_budget_filter or has_budget_text:
            score += 20

        # 2. Location (+20)
        has_city_filter = filters.get("city") is not None
        has_loc_text = bool(re.search(r'\b(location|kahan|address|area|near|paas|bangalore|mumbai|gurgaon|noida|hyderabad|pune|chennai|kolkata|delhi)\b', user_text))
        if has_city_filter or has_loc_text:
            score += 20

        # 3. Property Type (+20)
        has_type_filter = filters.get("property_type") is not None
        has_type_text = bool(re.search(r'\b(bhk|flat|apartment|villa|penthouse|studio|house)\b', user_text))
        if has_type_filter or has_type_text:
            score += 20

        # 4. Timeline (+20)
        has_timeline = any(re.search(r'\b' + re.escape(kw) + r'\b', user_text) for kw in self.TIMELINE_KEYWORDS)
        if has_timeline:
            score += 20

        # 5. Site Visit Intent (+20)
        if intent == "site_visit_request":
            score += 20

        return min(100, score)

    def should_escalate(self, session_data: Dict[str, Any]) -> bool:
        """
        Determines whether the conversation should be escalated to a human real estate agent:
        1. Negotiation intent for 2+ consecutive turns
        2. Escalation keywords present in user input
        3. Lead score >= 80 AND site_visit requested
        4. Low router confidence / fallback triggered for 3+ turns
        5. Call duration > 10 minutes (600 seconds)
        """
        user_text = (session_data.get("user_text") or "").lower()
        intent = session_data.get("intent") or ""
        score = session_data.get("lead_score", 0)
        session_id = session_data.get("session_id", "")
        duration = session_data.get("duration_seconds", 0)

        # Rule 1: Explicit Escalation Keywords
        if any(re.search(r'\b' + re.escape(kw) + r'\b', user_text) for kw in self.ESCALATION_KEYWORDS):
            return True

        # Rule 2: High Lead Score (>=80) + Site Visit Request
        if score >= 80 and intent == "site_visit_request":
            return True

        # Rule 3: Duration > 10 minutes
        if duration > 600:
            return True

        # Rule 4 & 5: Check session history turns
        history = self.sessions.get(session_id, [])
        recent_user_intents = [t.get("intent") for t in history if t.get("role") == "user"]
        if intent:
            recent_user_intents.append(intent)

        if len(recent_user_intents) >= 2:
            if recent_user_intents[-2:] == ["negotiation", "negotiation"]:
                return True

        # Check consecutive fallback / low confidence turns
        fallback_turns = [t for t in history if t.get("is_fallback") or "Fallback" in t.get("content", "")]
        if len(fallback_turns) >= 3:
            return True

        return False

    def process_text_input(self, session_id: str, user_text: str, duration_seconds: int = 0) -> Dict[str, Any]:
        """
        Processes multi-turn user text through language detection, RAG retrieval,
        dynamic LLM routing, lead scoring, and human escalation evaluation.
        """
        # Step 1: Language, Intent & Complexity Detection
        language = self.detector.detect_language(user_text)
        intent = self.detector.detect_intent(user_text)
        complexity = self.detector.estimate_complexity(user_text, intent)

        # Step 2: RAG Property Retrieval
        filters = self.retriever.extract_filters_from_text(user_text)
        properties = self.retriever.search(user_text, filters=filters, top_k=3)
        context = self.retriever.format_results_for_llm(properties)

        # Step 3: Manage Conversation History
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        history = self.sessions[session_id]

        # Step 4: Route to Dynamic LLM (with fallback to Gemini and natural conversation)
        llm_result = self.router.route(
            text=user_text,
            complexity=complexity,
            context=context,
            history=history,
            language=language,
            intent=intent,
            properties=properties
        )

        response_text = llm_result.get("response_text", "")

        # Calculate Lead Qualification Score
        eval_payload = {
            "session_id": session_id,
            "user_text": user_text,
            "filters_extracted": filters,
            "intent": intent,
            "duration_seconds": duration_seconds
        }
        lead_score = self.get_lead_score(eval_payload)
        eval_payload["lead_score"] = lead_score

        # Check Human Escalation
        escalate = self.should_escalate(eval_payload)

        # Append turn to history
        self.sessions[session_id].append({
            "role": "user",
            "content": user_text,
            "intent": intent,
            "language": language
        })
        self.sessions[session_id].append({
            "role": "assistant",
            "content": response_text,
            "is_fallback": llm_result.get("is_fallback", False),
            "model_used": llm_result.get("model_used")
        })

        return {
            "session_id": session_id,
            "user_text": user_text,
            "language": language,
            "intent": intent,
            "complexity": complexity,
            "filters_extracted": filters,
            "properties_found": properties,
            "response_text": response_text,
            "model_used": llm_result.get("model_used"),
            "tokens_used": llm_result.get("tokens_used", 0),
            "latency_ms": llm_result.get("latency_ms", 0.0),
            "estimated_cost_usd": llm_result.get("estimated_cost_usd", 0.0),
            "lead_score": lead_score,
            "should_escalate": escalate
        }
