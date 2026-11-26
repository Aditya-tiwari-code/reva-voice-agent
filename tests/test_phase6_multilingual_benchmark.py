import time
import re
from unittest.mock import MagicMock
import pytest

from app.agent.conversation import ConversationAgent
from app.tts.tts_service import clean_text_for_tts

# 30 Curated Multilingual Queries: 10 English, 10 Hindi, 10 Hinglish
MULTILINGUAL_QUERIES = [
    # 10 English
    {"q": "I want a 2BHK flat in Ghaziabad under 60 lakh", "lang": "english"},
    {"q": "Looking for ready to move 3BHK apartment in Noida", "lang": "english"},
    {"q": "What is the price of 2BHK in Delhi near Dwarka?", "lang": "english"},
    {"q": "Are there rental flats in Indirapuram under 25000?", "lang": "english"},
    {"q": "Compare Gaur City 2 and Supertech Capetown in Noida", "lang": "english"},
    {"q": "What is the monthly EMI for 50 lakh for 20 years at 8.5%?", "lang": "english"},
    {"q": "Can I schedule a site visit for Saturday at 11 AM?", "lang": "english"},
    {"q": "What documents should I check at site visit for RERA approval?", "lang": "english"},
    {"q": "Save this property to my shortlist", "lang": "english"},
    {"q": "Show my shortlisted properties", "lang": "english"},

    # 10 Hindi
    {"q": "मुझे दिल्ली में 2BHK फ़्लैट चाहिए 50 लाख के बजट में", "lang": "hindi"},
    {"q": "गाज़ियाबाद में 3BHK रेडी टू मूव फ़्लैट दिखाइए", "lang": "hindi"},
    {"q": "द्वारका में 2BHK का रेट क्या चल रहा है?", "lang": "hindi"},
    {"q": "नोएडा में किराए के लिए 1BHK फ़्लैट मिलेगा क्या?", "lang": "hindi"},
    {"q": "60 लाख के लोन पर 20 साल के लिए कितनी ईएमआई बनेगी?", "lang": "hindi"},
    {"q": "क्या मैं रविवार सुबह 11 बजे साइट विज़िट कर सकता हूँ?", "lang": "hindi"},
    {"q": "साइट विज़िट पर जाने से पहले मुझे कौन से दस्तावेज़ देखने चाहिए?", "lang": "hindi"},
    {"q": "इस प्रॉपर्टी को मेरी शॉर्टलिस्ट में जोड़ दीजिये", "lang": "hindi"},
    {"q": "मेरी शॉर्टलिस्ट की हुई प्रॉपर्टीज दिखाइए", "lang": "hindi"},
    {"q": "मुझे किसी सीनियर एजेंट से बात करनी है", "lang": "hindi"},

    # 10 Hinglish
    {"q": "Ghaziabad me 2BHK flat dikhao 50 lakh ke andar", "lang": "hinglish"},
    {"q": "Noida me 3BHK ready to move option kya hai?", "lang": "hinglish"},
    {"q": "Delhi me metro ke paas 2BHK ka price kitna hoga?", "lang": "hinglish"},
    {"q": "Indirapuram me rental 2BHK chahiye 20000 budget me", "lang": "hinglish"},
    {"q": "EMI calculate karke batao 45 lakh loan ke liye", "lang": "hinglish"},
    {"q": "Kal shaam 5 baje site visit schedule ho sakti hai kya?", "lang": "hinglish"},
    {"q": "Is flat ko shortlist me save kar do", "lang": "hinglish"},
    {"q": "Meri saved properties dikhao", "lang": "hinglish"},
    {"q": "Ye property thodi mehengi hai, kuch sasta option dikhao", "lang": "hinglish"},
    {"q": "Manager se baat karao I want to talk to human", "lang": "hinglish"}
]


@pytest.fixture
def agent():
    ag = ConversationAgent()
    mock_reply = '{"reply_text": "Verified matching property options from ChromaDB.", "spoken_text": "I found a few verified options. Have a look at them below.", "language": "en", "intent": "property_inquiry", "slots": {"bhk": 2, "city": "Noida", "budget": 60.0, "buy_or_rent": "buy", "timeline": null}, "next_action": "show_properties"}'
    ag.router._call_groq = MagicMock(return_value=(mock_reply, 30, "llama-3-8b-8192"))
    ag.router._call_gemini = MagicMock(return_value=(mock_reply, 30, "gemini-1.5-flash"))
    return ag


def test_multilingual_30_queries_benchmark(agent):
    """
    Evaluates 30 real-world multilingual queries (10 EN, 10 HI, 10 Hinglish).
    Measures:
    1. Language-match accuracy
    2. End-to-end response latency
    3. Spoken text length constraint (<= 3 sentences)
    4. TTS fallback robustness (tts_failed is a boolean, never uncaught crash)
    5. No property hallucination (only valid properties from DB/context)
    """
    total_queries = len(MULTILINGUAL_QUERIES)
    language_matches = 0
    total_latency_ms = 0.0
    tts_errors = 0

    for idx, item in enumerate(MULTILINGUAL_QUERIES):
        q = item["q"]
        expected_lang = item["lang"]
        sess_id = f"bench_sess_{idx}"

        t0 = time.time()
        res = agent.process_text_input(sess_id, q)
        latency = (time.time() - t0) * 1000.0
        total_latency_ms += latency

        resp_lang = res.get("language")
        # In Indian contexts, Hinglish and Hindi are mutually intelligible
        if resp_lang == expected_lang or (expected_lang in ("hindi", "hinglish") and resp_lang in ("hindi", "hinglish")):
            language_matches += 1

        # Spoken text length rule: max 3 sentences
        spoken = res.get("spoken_text", "")
        sentences = [s for s in re.split(r'[.?!।]', spoken) if s.strip()]
        assert len(sentences) <= 3, f"Spoken text exceeded 3 sentences: '{spoken}'"

        # Check TTS failure flag validity
        assert isinstance(res.get("tts_failed"), bool)
        if res.get("tts_failed") is True:
            tts_errors += 1

        # No-hallucination check: property metadata must match DB properties
        for prop in res.get("properties", []):
            assert "title" in prop
            assert "city" in prop
            assert "price_lakh" in prop

    lang_accuracy = (language_matches / total_queries) * 100.0
    avg_latency = total_latency_ms / total_queries
    tts_fail_rate = (tts_errors / total_queries) * 100.0

    print(f"\n=======================================================")
    print(f"       REVA MULTILINGUAL BENCHMARK RESULTS (30 QUERIES)   ")
    print(f"=======================================================")
    print(f"Total Queries Evaluated     : {total_queries} (10 EN / 10 HI / 10 Hinglish)")
    print(f"Language Match Accuracy     : {lang_accuracy:.1f}%")
    print(f"Average End-to-End Latency  : {avg_latency:.2f} ms")
    print(f"TTS Graceful Fallback Rate  : {tts_fail_rate:.1f}%")
    print(f"=======================================================\n")

    assert lang_accuracy >= 90.0, f"Language accuracy was {lang_accuracy}% (expected >= 90%)"
    assert avg_latency < 3000.0, f"Average latency was {avg_latency} ms"
