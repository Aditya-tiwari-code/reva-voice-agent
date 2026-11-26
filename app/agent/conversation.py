import re
from typing import Dict, Any, List
from app.stt.transcriber import HinglishTranscriber
from app.language.detector import LanguageDetector
from app.rag.retriever import PropertyRetriever
from app.router.llm_router import AdaptiveLLMRouter
from app.tts.tts_service import tts_service
from app.tools.financial_tools import (
    parse_and_calculate_emi,
    parse_and_estimate_affordability,
    compare_properties,
    get_site_visit_checklist
)
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
        self.session_states: Dict[str, Dict[str, Any]] = {}

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
        Supports Phase 1 structured replies (reply_text, spoken_text, slots, next_action)
        and multi-turn session language & slot tracking.
        """
        # Step 0: Session State Management (Language & Slots Memory)
        if session_id not in self.session_states:
            self.session_states[session_id] = {
                "language": "hinglish",
                "slots": {
                    "bhk": None,
                    "city": None,
                    "budget": None,
                    "buy_or_rent": "buy",
                    "timeline": None
                }
            }
        session_state = self.session_states[session_id]

        # Step 1: Language Detection & Session Language Mirroring
        detected_language = self.detector.detect_language(user_text)
        lower_user = user_text.lower().strip()
        words = set(re.findall(r'\b\w+\b', lower_user))
        has_devanagari = bool(re.search(r'[\u0900-\u097F]', user_text))
        prev_lang = session_state.get("language")

        short_ack_tokens = {"theek", "hai", "haan", "ha", "accha", "achha", "ok", "okay", "yes", "no", "sure", "sahi", "nahi", "shukriya", "dhanyawad", "bye", "ji"}
        is_short_ack = len(words) <= 3 and (words.issubset(short_ack_tokens) or len(words) == 0)

        if has_devanagari:
            active_language = "hindi"
        elif is_short_ack and prev_lang:
            active_language = prev_lang
        elif words.intersection(self.detector.HINGLISH_KEYWORDS):
            if prev_lang == "hindi" and len(words) <= 3:
                active_language = "hindi"
            else:
                active_language = "hinglish"
        elif prev_lang and len(words) <= 2:
            active_language = prev_lang
        else:
            active_language = detected_language

        session_state["language"] = active_language

        intent = self.detector.detect_intent(user_text)
        complexity = self.detector.estimate_complexity(user_text, intent)

        # Step 2: Multi-Turn Slot Accumulation and RAG Retrieval
        current_filters = self.retriever.extract_filters_from_text(user_text)

        # Update accumulated session slots
        if current_filters.get("bhk") is not None:
            session_state["slots"]["bhk"] = current_filters["bhk"]
        if current_filters.get("city") is not None:
            session_state["slots"]["city"] = current_filters["city"]
        if current_filters.get("max_price") is not None:
            session_state["slots"]["budget"] = current_filters["max_price"]
        if current_filters.get("transaction_type") is not None:
            session_state["slots"]["buy_or_rent"] = current_filters["transaction_type"]

        for kw in self.TIMELINE_KEYWORDS:
            if re.search(r'\b' + re.escape(kw) + r'\b', lower_user):
                session_state["slots"]["timeline"] = kw
                break

        # Merged filters for ChromaDB property retrieval
        merged_filters = dict(current_filters)
        if not merged_filters.get("city") and session_state["slots"].get("city"):
            merged_filters["city"] = session_state["slots"]["city"]
        if merged_filters.get("bhk") is None and session_state["slots"].get("bhk") is not None:
            merged_filters["bhk"] = session_state["slots"]["bhk"]
        if merged_filters.get("max_price") is None and session_state["slots"].get("budget") is not None:
            merged_filters["max_price"] = session_state["slots"]["budget"]
        if not merged_filters.get("transaction_type") and session_state["slots"].get("buy_or_rent"):
            merged_filters["transaction_type"] = session_state["slots"]["buy_or_rent"]

        properties = self.retriever.search(user_text, filters=merged_filters, top_k=3)
        is_default_trans = merged_filters.get("is_default_transaction", False)
        context = self.retriever.format_results_for_llm(properties, is_default_transaction=is_default_trans)

        # Step 3: Manage Conversation History
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        history = self.sessions[session_id]

        # Step 4: Check Python Financial & Assistance Tools (Strictly computed in code, never in LLM)
        emi_res = parse_and_calculate_emi(user_text, default_principal_lakh=session_state["slots"].get("budget"))
        afford_res = parse_and_estimate_affordability(user_text)
        is_chk = bool(re.search(r'\b(checklist|documents|paperwork|rera check)\b', lower_user))
        is_comp = bool(re.search(r'\b(compare\s+(?:option|both|these|the two|1|first|properties)|dono me se kaunsa|option 1 and 2|first and second|compare them)\b', lower_user)) and len(properties) >= 2
        is_save = bool(re.search(r'\b(shortlist|save this|save option|save flat|add to shortlist)\b', lower_user))
        is_show_shortlist = bool(re.search(r'\b(my shortlist|show shortlist|saved properties|saved flats)\b', lower_user))

        tool_executed = False
        llm_result = {}

        if emi_res:
            tool_executed = True
            reply_text = emi_res["text_summary"]
            spoken_text = emi_res["spoken_summary_hi"] if active_language in ("hindi", "hinglish") else emi_res["spoken_summary_en"]
            next_action = "ask_slot"
            llm_result = {"model_used": "python_emi_tool", "latency_ms": 1.0, "tokens_used": 0, "estimated_cost_usd": 0.0}
        elif afford_res:
            tool_executed = True
            reply_text = afford_res["text_summary"]
            spoken_text = afford_res["spoken_hi"] if active_language in ("hindi", "hinglish") else afford_res["spoken_en"]
            next_action = "show_properties"
            llm_result = {"model_used": "python_affordability_tool", "latency_ms": 1.0, "tokens_used": 0, "estimated_cost_usd": 0.0}
        elif is_chk:
            tool_executed = True
            chk = get_site_visit_checklist()
            reply_text = chk["checklist_text"]
            spoken_text = chk["spoken_hi"] if active_language in ("hindi", "hinglish") else chk["spoken_en"]
            next_action = "schedule_visit"
            llm_result = {"model_used": "python_checklist_tool", "latency_ms": 1.0, "tokens_used": 0, "estimated_cost_usd": 0.0}
        elif is_comp:
            tool_executed = True
            comp = compare_properties(properties[0], properties[1])
            reply_text = comp["table_markdown"]
            spoken_text = comp["spoken_hi"] if active_language in ("hindi", "hinglish") else comp["spoken_en"]
            next_action = "schedule_visit"
            llm_result = {"model_used": "python_comparison_tool", "latency_ms": 1.0, "tokens_used": 0, "estimated_cost_usd": 0.0}
        elif is_save:
            tool_executed = True
            session_state.setdefault("shortlist", [])
            if properties:
                session_state["shortlist"].append(properties[0])
            count = len(session_state.get("shortlist", []))
            reply_text = f"✅ Property has been saved to your shortlist! You currently have {count} saved property option(s)."
            spoken_text = f"मैंने यह प्रॉपर्टी आपकी शॉर्टलिस्ट में सेव कर दी है।" if active_language in ("hindi", "hinglish") else f"Added to your shortlist! You have {count} saved properties."
            next_action = "show_properties"
            llm_result = {"model_used": "python_shortlist_tool", "latency_ms": 1.0, "tokens_used": 0, "estimated_cost_usd": 0.0}
        elif is_show_shortlist:
            tool_executed = True
            saved = session_state.get("shortlist", [])
            if saved:
                properties = saved
                count = len(saved)
                reply_text = f"📋 Here are your **{count}** saved properties from your shortlist:"
                spoken_text = f"आपकी शॉर्टलिस्ट में {count} प्रॉपर्टीज सेव हैं।" if active_language in ("hindi", "hinglish") else f"Here are your {count} saved properties."
            else:
                reply_text = "Your shortlist is currently empty. Whenever you like a property listing, simply say 'Save this one'!"
                spoken_text = "आपकी शॉर्टलिस्ट अभी खाली है। किसी भी प्रॉपर्टी को सेव करने के लिए 'save this' कहें।" if active_language in ("hindi", "hinglish") else "Your shortlist is currently empty. Say save this to add any option."
            next_action = "show_properties"
            llm_result = {"model_used": "python_shortlist_tool", "latency_ms": 1.0, "tokens_used": 0, "estimated_cost_usd": 0.0}

        # Step 5: Route to Dynamic LLM if not handled by dedicated tool
        if not tool_executed:
            # Phase 8: Tone adaptation — if user message is very short (≤4 words), shorten reply
            is_hurried = len(words) <= 4

            llm_result = self.router.route(
                text=user_text,
                complexity=complexity,
                context=context,
                history=history,
                language=active_language,
                intent=intent,
                properties=properties,
                is_default_transaction=is_default_trans,
                filters=merged_filters
            )
            reply_text = llm_result.get("reply_text") or llm_result.get("response_text", "")
            spoken_text = llm_result.get("spoken_text") or reply_text
            next_action = llm_result.get("next_action") or ("show_properties" if properties else "ask_slot")

            # Phase 11: Trust/safety — if no properties found, say so and suggest alternatives
            if not properties and intent in ("property_inquiry", "price_inquiry", "site_visit_request"):
                honesty_note = (
                    " मुझे इस समय आपके फिल्टर के अनुसार कोई प्रॉपर्टी नहीं मिली। थोड़ा बजट बढ़ाकर या पास के इलाके में देखें?"
                    if active_language in ("hindi", "hinglish")
                    else " I couldn't find an exact match right now. Try a nearby locality or slightly higher budget?"
                )
                if "no properties" not in reply_text.lower() and "nahi mila" not in reply_text.lower():
                    reply_text = reply_text.rstrip() + honesty_note
                    spoken_text = spoken_text.rstrip() + (
                        " कोई बिल्कुल सही मिलान नहीं है — पास के विकल्प देखते हैं।"
                        if active_language in ("hindi", "hinglish")
                        else " No exact match — let me suggest nearby alternatives."
                    )

            # Phase 11: Transparency disclaimer for financial/legal details not in DB
            sensitive_patterns = r'\b(rera|registration|legal status|school distance|metro distance|construction status|possession date)\b'
            if re.search(sensitive_patterns, user_text, re.IGNORECASE):
                disclaimer = (
                    "\n\n⚠️ _यह जानकारी हमारे पास उपलब्ध नहीं है — कृपया साइट विज़िट के दौरान confirm करें।_"
                    if active_language in ("hindi", "hinglish")
                    else "\n\n⚠️ _I don't have that detail in our records — please confirm during your site visit._"
                )
                if "confirm" not in reply_text.lower():
                    reply_text = reply_text.rstrip() + disclaimer

        # Calculate Lead Qualification Score
        eval_payload = {
            "session_id": session_id,
            "user_text": user_text,
            "filters_extracted": merged_filters,
            "intent": intent,
            "duration_seconds": duration_seconds
        }
        lead_score = self.get_lead_score(eval_payload)
        eval_payload["lead_score"] = lead_score

        # Check Human Escalation
        escalate = self.should_escalate(eval_payload)
        if escalate:
            next_action = "handoff"

        lead_category = "hot" if lead_score >= 75 else ("warm" if lead_score >= 45 else "cold")
        lead_reason = (
            "High intent: budget, location, and site visit requested" if lead_category == "hot" else
            ("Active engagement with property search criteria" if lead_category == "warm" else "Initial exploration")
        )

        # Append turn to history
        self.sessions[session_id].append({
            "role": "user",
            "content": user_text,
            "intent": intent,
            "language": active_language
        })
        self.sessions[session_id].append({
            "role": "assistant",
            "content": reply_text,
            "spoken_text": spoken_text,
            "is_fallback": llm_result.get("is_fallback", False),
            "model_used": llm_result.get("model_used")
        })

        # Clean properties array with standard keys for frontend cards
        clean_properties = []
        for p in properties:
            meta = p.get("metadata") or {}
            clean_properties.append({
                "id": p.get("id") or meta.get("id"),
                "title": meta.get("title") or "Verified Property",
                "location": meta.get("location") or "",
                "city": meta.get("city") or "",
                "price_lakh": meta.get("price_lakh"),
                "bhk": meta.get("bhk"),
                "area_sqft": meta.get("area_sqft"),
                "transaction_type": meta.get("transaction_type") or "buy",
                "availability": meta.get("availability") or "Ready to Move",
                "amenities": meta.get("amenities") or "",
                "is_alternative": p.get("is_alternative", False)
            })

        # Step 6: Text-to-Speech Synthesis
        tts_result = tts_service.generate_speech(spoken_text, language=active_language)
        audio_url = tts_result.get("audio_url")
        tts_failed = tts_result.get("tts_failed", False)

        # Phase 8: Pre-generate filler audio (cached, near-zero latency on cache hit)
        filler_result = tts_service.get_filler_audio(language=active_language)
        filler_audio_url = filler_result.get("audio_url")

        # Phase 10: End-of-session recap (spoken + text)
        shortlist = session_state.get("shortlist", [])
        recap_text = None
        recap_spoken = None
        if shortlist or session_state["slots"].get("timeline"):
            sl_count = len(shortlist)
            timeline = session_state["slots"].get("timeline") or ""
            if sl_count > 0 and timeline:
                recap_text = f"You liked {sl_count} property(ies) and mentioned '{timeline}' as your timeline."
                recap_spoken = (
                    f"आपने {sl_count} प्रॉपर्टी पसंद की और '{timeline}' timeline बताई।"
                    if active_language in ("hindi", "hinglish")
                    else recap_text
                )
            elif sl_count > 0:
                recap_text = f"You have {sl_count} saved property(ies) in your shortlist."
                recap_spoken = (
                    f"आपकी शॉर्टलिस्ट में {sl_count} प्रॉपर्टी सेव हैं।"
                    if active_language in ("hindi", "hinglish")
                    else recap_text
                )

        return {
            "session_id": session_id,
            "user_text": user_text,
            "language": active_language,
            "intent": intent,
            "complexity": complexity,
            "filters_extracted": merged_filters,
            "properties_found": properties,
            "properties": clean_properties,
            "response_text": reply_text,
            "reply_text": reply_text,
            "spoken_text": spoken_text,
            "audio_url": audio_url,
            "tts_failed": tts_failed,
            "filler_audio_url": filler_audio_url,
            "slots": session_state["slots"],
            "next_action": next_action,
            "model_used": llm_result.get("model_used"),
            "tokens_used": llm_result.get("tokens_used", 0),
            "latency_ms": llm_result.get("latency_ms", 0.0),
            "estimated_cost_usd": llm_result.get("estimated_cost_usd", 0.0),
            "lead_score": lead_score,
            "lead_category": lead_category,
            "lead_reason": lead_reason,
            "shortlist_count": len(session_state.get("shortlist", [])),
            "should_escalate": escalate,
            "recap_text": recap_text,
            "recap_spoken": recap_spoken,
        }
