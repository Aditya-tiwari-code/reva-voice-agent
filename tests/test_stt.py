import pytest
from app.stt.transcriber import WhisperTranscriber

def test_transcriber_initialization():
    transcriber = WhisperTranscriber(model_size="base")
    assert transcriber.model_size == "base"

@pytest.mark.asyncio
async def test_transcribe_audio_stub():
    transcriber = WhisperTranscriber()
    result = await transcriber.transcribe_audio(b"dummy_audio")
    assert "text" in result
    assert "language" in result
