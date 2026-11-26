import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest

from app.tts.tts_service import clean_text_for_tts, TTSService
from app.main import app

client = TestClient(app)


def test_clean_text_english_normalization():
    """Verify cleaning of markdown, BHK, currency, and locality pronunciation in English."""
    raw = "• Check out this *2BHK* in Indirapuram for ₹85 lakh! Size: 1200 sq ft. https://reva.ai/prop1"
    cleaned = clean_text_for_tts(raw, language="english")

    assert "•" not in cleaned
    assert "*" not in cleaned
    assert "https://" not in cleaned
    assert "two B H K" in cleaned
    assert "85 lakh rupees" in cleaned
    assert "square feet" in cleaned
    assert "Indira-puram" in cleaned


def test_clean_text_hindi_normalization():
    """Verify cleaning and normalization for Hindi / Devanagari text."""
    raw = "गाज़ियाबाद में 2BHK फ्लैट ₹50 lakh में उपलब्ध है, 950 sq ft."
    cleaned = clean_text_for_tts(raw, language="hindi")

    assert "दो बी एच के" in cleaned
    assert "लाख रुपये" in cleaned
    assert "स्क्वायर फीट" in cleaned


def test_tts_audio_caching(tmp_path):
    """Verify audio caching by hash: repeated generation returns cached=True without re-synthesizing."""
    tts = TTSService(cache_dir=tmp_path)

    with patch.object(tts, '_synthesize_worker') as mock_worker:
        # First call: cache miss, invokes worker
        res1 = tts.generate_speech("I found 3 flats in Ghaziabad.", language="english")
        assert res1["tts_failed"] is False
        assert res1["audio_url"] is not None
        mock_worker.assert_called_once()

        # Simulate file created by worker on disk
        cache_file = tmp_path / Path(res1["audio_path"]).name
        cache_file.write_bytes(b"dummy_mp3_content")

        # Second call: cache hit, worker NOT called again
        mock_worker.reset_mock()
        res2 = tts.generate_speech("I found 3 flats in Ghaziabad.", language="english")
        assert res2["cached"] is True
        assert res2["audio_url"] == res1["audio_url"]
        mock_worker.assert_not_called()


def test_tts_graceful_failure_fallback(tmp_path):
    """Verify graceful fallback with tts_failed=True when gTTS fails."""
    tts = TTSService(cache_dir=tmp_path)

    with patch.object(tts, '_synthesize_worker', side_effect=Exception("Connection refused")):
        res = tts.generate_speech("Hello test error handling", language="english")
        assert res["tts_failed"] is True
        assert res["audio_url"] is None
        assert "clean_text" in res


def test_fastapi_tts_endpoint():
    """Test POST /tts endpoint returns structured response."""
    with patch("app.main.tts_service.generate_speech") as mock_gen:
        mock_gen.return_value = {
            "audio_url": "/tts/audio/test1234.mp3",
            "audio_path": "dummy.mp3",
            "tts_failed": False,
            "clean_text": "hello",
            "cached": True
        }
        resp = client.post("/tts", json={"text": "Hello test", "language": "english"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_url"] == "/tts/audio/test1234.mp3"
        assert data["tts_failed"] is False
