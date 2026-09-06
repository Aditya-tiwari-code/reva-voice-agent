import os
import io
import re
import tempfile
from typing import Dict, Any, List

class HinglishTranscriber:
    """
    Speech-to-Text transcriber using faster-whisper.
    Optimized for English, Hindi, and Hinglish real estate voice queries.
    """

    def __init__(self, model_size: str = "small", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    @property
    def model(self):
        """Lazy loader for faster-whisper model."""
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
        return self._model

    def normalize_text(self, text: str) -> str:
        """
        Clean and normalize transcribed text:
        - Converts to lowercase
        - Standardizes common real estate terms (bhk, sqft, lakh, crore)
        - Removes extra spaces and punctuation artifacts
        """
        if not text:
            return ""

        text = text.lower().strip()

        # Common Hinglish/Real Estate replacements & cleanups
        replacements = [
            (r"\bb\.?h\.?k\b", "bhk"),
            (r"\bsq\.?\s*ft\.?", "sqft"),
            (r"\bsquare\s+feet\b", "sqft"),
            (r"\bsquare\s+foot\b", "sqft"),
            (r"\blacs?\b", "lakh"),
            (r"\bcrs?\b", "crore"),
            (r"\s+", " ")
        ]

        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)

        return text.strip()

    def transcribe_file(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio from file path.
        Returns: { 'text': str, 'language': str, 'segments': list, 'confidence': float }
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        segments_raw, info = self.model.transcribe(audio_path, beam_size=5)

        segment_list: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []
        total_prob = 0.0
        count = 0

        for segment in segments_raw:
            full_text_parts.append(segment.text)
            prob = getattr(segment, "avg_logprob", 0.0)
            # Convert avg_logprob to approximate probability confidence 0-1 range
            confidence_est = min(1.0, max(0.0, float(2.71828 ** prob)))
            total_prob += confidence_est
            count += 1
            segment_list.append({
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": round(confidence_est, 4)
            })

        raw_text = " ".join(full_text_parts)
        normalized_text = self.normalize_text(raw_text)
        avg_confidence = round(total_prob / count, 4) if count > 0 else 0.0

        return {
            "text": normalized_text,
            "raw_text": raw_text.strip(),
            "language": info.language,
            "segments": segment_list,
            "confidence": avg_confidence
        }

    def transcribe_bytes(self, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Transcribe raw audio bytes (useful for webhooks and audio streams).
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        try:
            return self.transcribe_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
