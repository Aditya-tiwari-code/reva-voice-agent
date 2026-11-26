import os
import re
import io
import time
import hashlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Dict, Any, Optional, List
from gtts import gTTS

logger = logging.getLogger(__name__)

# Cache directory for synthesized audio
AUDIO_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Pronunciation mappings for Indian localities and common real estate terms
INDIAN_PRONUNCIATION_EN = {
    r"\bIndirapuram\b": "Indira-puram",
    r"\bVaishali\b": "Vye-shaali",
    r"\bRaj Nagar Extension\b": "Raaj Nagar Extension",
    r"\bDwarka\b": "Dwaar-ka",
    r"\bGachibowli\b": "Gaachi-bowli",
    r"\bKoramangala\b": "Kora-mangala",
    r"\bWhitefield\b": "White-field",
    r"\bHinglish\b": "Hing-lish",
}

INDIAN_PRONUNCIATION_HI = {
    r"\bIndirapuram\b": "इंदिरापुरम",
    r"\bVaishali\b": "वैशाली",
    r"\bRaj Nagar Extension\b": "राज नगर एक्सटेंशन",
    r"\bDwarka\b": "द्वारका",
    r"\bGachibowli\b": "गाचीबोवली",
    r"\bWhitefield\b": "व्हाइटफ़ील्ड",
    r"\bNoida\b": "नोएडा",
    r"\bDelhi\b": "दिल्ली",
    r"\bGhaziabad\b": "गाज़ियाबाद",
    r"\bGurgaon\b": "गुड़गांव",
    r"\bBangalore\b": "बैंगलोर",
    r"\bMumbai\b": "मुंबई",
    r"\bHyderabad\b": "हैदराबाद",
    r"\bPune\b": "पुणे",
}

DIGIT_WORDS_EN = {
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}

DIGIT_WORDS_HI = {
    "1": "एक",
    "2": "दो",
    "3": "तीन",
    "4": "चार",
    "5": "पांच",
}


def clean_text_for_tts(text: str, language: str = "english") -> str:
    """
    Cleans text for natural speech synthesis:
    - Removes markdown syntax, bullets, emojis, URLs
    - Normalizes BHK, prices, square feet, and Indian number formats
    - Applies Indian locality pronunciation mappings
    """
    if not text:
        return ""

    s = text.strip()

    # 1. Remove URLs
    s = re.sub(r'https?://\S+', '', s)

    # 2. Remove emojis and special formatting characters
    s = re.sub(r'[\U00010000-\U0010ffff]', '', s)
    s = re.sub(r'[•\*\#\_\[\]\(\)\{\}\<\>\|\\~`^]', ' ', s)

    lang_clean = (language or "english").lower().strip()
    is_hindi_family = lang_clean in ("hindi", "hinglish") or bool(re.search(r'[\u0900-\u097F]', s))

    # 3. Currency and Number normalization
    if is_hindi_family:
        # Hindi / Hinglish normalization
        for digit, word in DIGIT_WORDS_HI.items():
            s = re.sub(rf'\b{digit}\s*[bB][hH][kK]\b', f'{word} बी एच के', s)

        s = re.sub(r'\b[bB][hH][kK]\b', 'बी एच के', s)
        s = re.sub(r'₹?\s*(\d+(?:\.\d+)?)\s*(?:lakh|Lacs|lac|लाख)', r'\1 लाख रुपये', s, flags=re.IGNORECASE)
        s = re.sub(r'₹?\s*(\d+(?:\.\d+)?)\s*(?:crore|cr|Cr|करोड़)', r'\1 करोड़ रुपये', s, flags=re.IGNORECASE)
        s = re.sub(r'₹\s*(\d+)', r'\1 रुपये', s)
        s = re.sub(r'\b(?:sq\s*ft|sqft|sq\.\s*ft|स्क्वेयर फीट)\b', 'स्क्वायर फीट', s, flags=re.IGNORECASE)

        for pat, repl in INDIAN_PRONUNCIATION_HI.items():
            s = re.sub(pat, repl, s, flags=re.IGNORECASE)
    else:
        # English normalization
        for digit, word in DIGIT_WORDS_EN.items():
            s = re.sub(rf'\b{digit}\s*[bB][hH][kK]\b', f'{word} B H K', s)

        s = re.sub(r'\b[bB][hH][kK]\b', 'B H K', s)

        # Indian spoken number shortcuts
        s = re.sub(r'\bdedh\s+crore\b', 'one point five crore rupees', s, flags=re.IGNORECASE)
        s = re.sub(r'\bsaadhe\s+teen\s+crore\b', 'three point five crore rupees', s, flags=re.IGNORECASE)
        s = re.sub(r'\bpachaas\s+lakh\b', 'fifty lakh rupees', s, flags=re.IGNORECASE)
        s = re.sub(r'₹?\s*(\d+)\s*[lL]\b', r'\1 lakh rupees', s)
        s = re.sub(r'₹?\s*(\d+(?:\.\d+)?)\s*(?:lakh|Lacs|lac)\b', r'\1 lakh rupees', s, flags=re.IGNORECASE)
        s = re.sub(r'₹?\s*(\d+(?:\.\d+)?)\s*(?:crore|cr|Cr)\b', r'\1 crore rupees', s, flags=re.IGNORECASE)
        s = re.sub(r'₹\s*(\d+)', r'\1 rupees', s)
        s = re.sub(r'\b(?:sq\s*ft|sqft|sq\.\s*ft)\b', 'square feet', s, flags=re.IGNORECASE)

        for pat, repl in INDIAN_PRONUNCIATION_EN.items():
            s = re.sub(pat, repl, s, flags=re.IGNORECASE)

    # 4. Clean extra whitespaces and slashes
    s = re.sub(r'[/]', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    s = s.strip()

    return s


class TTSService:
    """
    Production-grade Text-to-Speech service using gTTS with:
    - Indian English (tld='co.in') and Hindi (lang='hi') accents
    - Hash-based disk audio caching for zero-latency repeated utterances
    - Strict timeout (~5s) and graceful fallback with tts_failed flag
    """

    def __init__(self, cache_dir: Optional[Path] = None, timeout_seconds: float = 5.0):
        self.cache_dir = cache_dir or AUDIO_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=3)

    def _get_lang_and_tld(self, language: str) -> tuple[str, str]:
        lang_clean = (language or "english").lower().strip()
        if lang_clean in ("hindi", "hinglish"):
            return "hi", "co.in"
        return "en", "co.in"

    def _synthesize_worker(self, cleaned_text: str, lang_code: str, tld: str, file_path: Path):
        tts = gTTS(text=cleaned_text, lang=lang_code, tld=tld, slow=False)
        tts.save(str(file_path))

    def generate_speech(self, text: str, language: str = "english") -> Dict[str, Any]:
        """
        Synthesizes spoken text into an audio file.
        Returns dict with:
        - audio_url: URL to fetch the audio file (or None if failed)
        - audio_path: absolute path on disk
        - tts_failed: bool indicating if gTTS failed or timed out
        - clean_text: the processed text passed to TTS
        - cached: bool indicating cache hit
        """
        if not text or not text.strip():
            return {
                "audio_url": None,
                "audio_path": None,
                "tts_failed": False,
                "clean_text": "",
                "cached": False
            }

        cleaned = clean_text_for_tts(text, language=language)
        lang_code, tld = self._get_lang_and_tld(language)

        # Hash key for deterministic audio caching
        hash_src = f"{cleaned}___{lang_code}___{tld}".encode("utf-8")
        cache_hash = hashlib.md5(hash_src).hexdigest()
        cache_filename = f"{cache_hash}.mp3"
        cache_filepath = self.cache_dir / cache_filename
        audio_url = f"/tts/audio/{cache_filename}"

        # 1. Return immediately on cache hit
        if cache_filepath.exists() and cache_filepath.stat().st_size > 0:
            return {
                "audio_url": audio_url,
                "audio_path": str(cache_filepath),
                "tts_failed": False,
                "clean_text": cleaned,
                "cached": True
            }

        # 2. Synthesize with timeout guard
        try:
            future = self._executor.submit(
                self._synthesize_worker,
                cleaned_text=cleaned,
                lang_code=lang_code,
                tld=tld,
                file_path=cache_filepath
            )
            future.result(timeout=self.timeout_seconds)

            return {
                "audio_url": audio_url,
                "audio_path": str(cache_filepath),
                "tts_failed": False,
                "clean_text": cleaned,
                "cached": False
            }
        except TimeoutError:
            logger.warning("TTS synthesis timed out after %.1fs for: %s", self.timeout_seconds, cleaned[:50])
            if cache_filepath.exists():
                try:
                    cache_filepath.unlink()
                except Exception:
                    pass
            return {
                "audio_url": None,
                "audio_path": None,
                "tts_failed": True,
                "clean_text": cleaned,
                "cached": False,
                "error": "TTS synthesis timed out"
            }
        except Exception as e:
            logger.warning("TTS synthesis failed (%s): %s", type(e).__name__, e)
            if cache_filepath.exists():
                try:
                    cache_filepath.unlink()
                except Exception:
                    pass
            return {
                "audio_url": None,
                "audio_path": None,
                "tts_failed": True,
                "clean_text": cleaned,
                "cached": False,
                "error": str(e)
            }


def cleanup_old_audio_files(cache_dir: Path, max_age_hours: int = 24) -> int:
    """
    Removes audio files older than max_age_hours from the cache directory.
    Returns count of files removed. Safe to call on startup or via a background scheduler.
    """
    removed = 0
    if not cache_dir.exists():
        return 0
    cutoff = time.time() - max_age_hours * 3600
    for f in cache_dir.glob("*.mp3"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except Exception:
            pass
    logger.info("Audio cache cleanup: removed %d file(s) older than %dh", removed, max_age_hours)
    return removed


def split_into_sentences(text: str) -> List[str]:
    """
    Splits text into individual sentences for streaming TTS.
    Handles English and Hindi sentence endings.
    """
    # Split on . ! ? and Hindi danda (।)
    parts = re.split(r'(?<=[.!?।])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


    def generate_speech_sentences(self, text: str, language: str = "english") -> List[Dict[str, Any]]:
        """
        Phase 8: Sentence-by-sentence streaming TTS.
        Splits text into sentences and generates audio for each.
        Returns a list of per-sentence audio results so the frontend can
        play sentence 1 while sentence 2 is still generating.
        """
        sentences = split_into_sentences(text)
        results = []
        for sentence in sentences:
            result = self.generate_speech(sentence, language=language)
            results.append({
                "sentence": sentence,
                "audio_url": result.get("audio_url"),
                "tts_failed": result.get("tts_failed", False),
                "cached": result.get("cached", False)
            })
        return results

    def get_filler_audio(self, language: str = "english") -> Dict[str, Any]:
        """
        Phase 8: Returns a short filler audio clip (played immediately while retrieval runs).
        Filler is generated/cached like any other speech.
        """
        FILLERS = {
            "english": "Let me check that for you, one moment.",
            "hindi": "एक सेकंड, देखती हूं।",
            "hinglish": "एक second रुकिए, देखती हूं।",
        }
        lang_key = (language or "english").lower().strip()
        filler_text = FILLERS.get(lang_key, FILLERS["english"])
        return self.generate_speech(filler_text, language=lang_key)


# Singleton service instance
tts_service = TTSService()
