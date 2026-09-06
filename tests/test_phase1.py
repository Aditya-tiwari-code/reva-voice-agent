import os
import tempfile
import pytest
from app.language.detector import LanguageDetector
from app.tts.synthesizer import MultilingualSynthesizer
from app.stt.transcriber import HinglishTranscriber


@pytest.fixture
def detector():
    return LanguageDetector()


@pytest.fixture
def synthesizer():
    return MultilingualSynthesizer()


@pytest.fixture
def transcriber():
    return HinglishTranscriber(model_size="tiny")


# ==========================================
# 1. LANGUAGE DETECTION TESTS (5 Samples)
# ==========================================
def test_language_detection_hindi_devanagari(detector):
    text = "नमस्ते, मुझे फ्लैट की जानकारी चाहिए"
    assert detector.detect_language(text) == "hindi"


def test_language_detection_pure_english(detector):
    text = "What is the price of a 3BHK luxury apartment in Bangalore?"
    assert detector.detect_language(text) == "english"


def test_language_detection_hinglish_1(detector):
    text = "Bhai Gachibowli me 2BHK flat ka rent kitna hai?"
    assert detector.detect_language(text) == "hinglish"


def test_language_detection_hinglish_2(detector):
    text = "Is project me ready to move flats available hain kya?"
    assert detector.detect_language(text) == "hinglish"


def test_language_detection_hinglish_mixed_script(detector):
    text = "Gachibowli में 3BHK flat का price kitna hai?"
    assert detector.detect_language(text) == "hinglish"


# ==========================================
# 2. INTENT DETECTION TESTS (10 Samples)
# ==========================================
def test_intent_price_inquiry(detector):
    text = "Whitefield me 3BHK flat ka price kitna hai?"
    assert detector.detect_intent(text) == "price_inquiry"


def test_intent_availability_check(detector):
    text = "Is project me ready to move flats available hain?"
    assert detector.detect_intent(text) == "availability_check"


def test_intent_location_query(detector):
    text = "Property kahan located hai address batao"
    assert detector.detect_intent(text) == "location_query"


def test_intent_property_details(detector):
    text = "Square feet kitna hai and parking details batao"
    assert detector.detect_intent(text) == "property_details"


def test_intent_site_visit_request(detector):
    text = "Mujhe kal site visit arrange karni hai dekhna hai"
    assert detector.detect_intent(text) == "site_visit_request"


def test_intent_negotiation(detector):
    text = "Price thoda kam ho sakta hai kya best discount batao"
    assert detector.detect_intent(text) == "negotiation"


def test_intent_comparison(detector):
    text = "Sobha Neopolis and Prestige high fields me kaunsa better hai compare karo"
    assert detector.detect_intent(text) == "comparison"


def test_intent_greeting(detector):
    text = "Hello namaste good morning"
    assert detector.detect_intent(text) == "greeting"


def test_intent_unknown(detector):
    text = "Random unrelated text sentence"
    assert detector.detect_intent(text) == "unknown"


def test_intent_price_inquiry_alternate(detector):
    text = "Kitna cost padega is 2bhk flat ka budget batao"
    assert detector.detect_intent(text) == "price_inquiry"


# ==========================================
# 3. COMPLEXITY ESTIMATION TESTS (6 Samples)
# ==========================================
def test_complexity_simple_price(detector):
    text = "What is the price of 2BHK?"
    intent = detector.detect_intent(text)
    assert detector.estimate_complexity(text, intent) == "simple"


def test_complexity_simple_availability(detector):
    text = "Is this property available for rent?"
    intent = detector.detect_intent(text)
    assert detector.estimate_complexity(text, intent) == "simple"


def test_complexity_simple_greeting(detector):
    text = "Namaste hello"
    intent = detector.detect_intent(text)
    assert detector.estimate_complexity(text, intent) == "simple"


def test_complexity_complex_negotiation(detector):
    text = "Mujhe price negotiate karna hai best discount kya de sakte ho?"
    intent = detector.detect_intent(text)
    assert detector.estimate_complexity(text, intent) == "complex"


def test_complexity_complex_comparison(detector):
    text = "Sobha aur Prestige me se kaunsa project better hai and kahan amenities achi hain?"
    intent = detector.detect_intent(text)
    assert detector.estimate_complexity(text, intent) == "complex"


def test_complexity_complex_unknown_long(detector):
    text = "I am thinking about buying something but not sure maybe next year or maybe now if financing works out with bank loan"
    intent = detector.detect_intent(text)
    assert detector.estimate_complexity(text, intent) == "complex"


# ==========================================
# 4. TTS SYNTHESIS TESTS (File & Bytes)
# ==========================================
def test_tts_synthesize_file(synthesizer):
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_audio.mp3")
        result_path = synthesizer.synthesize("Namaste, welcome to REVA", language="hinglish", output_path=output_file)
        assert os.path.exists(result_path)
        assert os.path.getsize(result_path) > 0


def test_tts_synthesize_to_bytes(synthesizer):
    audio_bytes = synthesizer.synthesize_to_bytes("Hello, how can I help you find a property?", language="english")
    assert isinstance(audio_bytes, bytes)
    assert len(audio_bytes) > 0


# ==========================================
# 5. STT TRANSCRIBER TESTS (Normalization & Instantiation)
# ==========================================
def test_stt_normalize_text(transcriber):
    raw_text = "  3 B.H.K flat 1200 Sq. Ft. at 90 Lacs  "
    normalized = transcriber.normalize_text(raw_text)
    assert normalized == "3 bhk flat 1200 sqft at 90 lakh"


def test_stt_transcriber_initialization(transcriber):
    assert transcriber.model_size == "tiny"
