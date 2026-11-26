import os
from pathlib import Path
from dotenv import load_dotenv

# Locate and load the .env file from root project directory
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

def reload_env():
    """Reloads environment variables directly from .env file with override=True."""
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)
    else:
        load_dotenv(override=True)

# Initial load
reload_env()

class Settings:
    @property
    def GROQ_API_KEY(self) -> str:
        reload_env()
        val = os.getenv("GROQ_API_KEY", "")
        return val.strip().strip('"').strip("'")

    @property
    def GEMINI_API_KEY(self) -> str:
        reload_env()
        val = os.getenv("GEMINI_API_KEY", "")
        return val.strip().strip('"').strip("'")

    @property
    def GROQ_MODEL(self) -> str:
        return os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip().strip('"').strip("'")

    @property
    def GEMINI_MODEL(self) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip().strip('"').strip("'")

    @property
    def TWILIO_ACCOUNT_SID(self) -> str:
        return os.getenv("TWILIO_ACCOUNT_SID", "").strip()

    @property
    def TWILIO_AUTH_TOKEN(self) -> str:
        return os.getenv("TWILIO_AUTH_TOKEN", "").strip()

    @property
    def TWILIO_PHONE_NUMBER(self) -> str:
        return os.getenv("TWILIO_PHONE_NUMBER", "").strip()

    @property
    def DATABASE_URL(self) -> str:
        return os.getenv("DATABASE_URL", "sqlite:///./reva.db").strip()

    @property
    def HOST(self) -> str:
        return os.getenv("HOST", "0.0.0.0").strip()

    @property
    def PORT(self) -> int:
        return int(os.getenv("PORT", 8000))

settings = Settings()
