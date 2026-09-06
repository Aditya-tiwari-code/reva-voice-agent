import os
import io
from gtts import gTTS

class MultilingualSynthesizer:
    """
    Text-to-Speech synthesizer supporting Hindi, English, and Hinglish using gTTS.
    """

    LANG_MAPPING = {
        "hindi": "hi",
        "english": "en",
        "hinglish": "hi"  # Hindi TTS pronunciation handles Hinglish text effectively
    }

    def _get_lang_code(self, language: str) -> str:
        """Map input language identifier to gTTS language code."""
        lang_clean = (language or "english").lower().strip()
        return self.LANG_MAPPING.get(lang_clean, "en")

    def synthesize(self, text: str, language: str = "english", output_path: str = "output.mp3") -> str:
        """
        Synthesizes text into an MP3 file at output_path.
        Returns the output file path.
        """
        if not text or not text.strip():
            raise ValueError("Text to synthesize cannot be empty.")

        lang_code = self._get_lang_code(language)
        tts = gTTS(text=text.strip(), lang=lang_code, slow=False)

        # Create output parent directory if it does not exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        tts.save(output_path)
        return output_path

    def synthesize_to_bytes(self, text: str, language: str = "english") -> bytes:
        """
        Synthesizes text into in-memory audio bytes (for streaming / websocket delivery).
        """
        if not text or not text.strip():
            raise ValueError("Text to synthesize cannot be empty.")

        lang_code = self._get_lang_code(language)
        tts = gTTS(text=text.strip(), lang=lang_code, slow=False)

        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
