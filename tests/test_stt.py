import pytest
from app.stt.transcriber import HinglishTranscriber

def test_transcriber_initialization():
    transcriber = HinglishTranscriber(model_size="base")
    assert transcriber.model_size == "base"

def test_transcribe_audio_stub():
    transcriber = HinglishTranscriber()
    normalized = transcriber.normalize_text("3 B.H.K flat")
    assert normalized == "3 bhk flat"
