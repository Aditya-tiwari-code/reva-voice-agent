# REVA — Real Estate Voice Agent

**REVA** is a **Cost-Aware Multilingual AI Voice Agent** designed specifically for **Real Estate Lead Qualification**. It handles inbound call queries, transcribes user input across Hindi/English/Hinglish, retrieves matching properties using vector search (ChromaDB), dynamically routes prompts across low-cost and high-capability LLMs (Groq & Gemini), and scores leads in real-time.

---

## 🏗️ Architecture & Features

- **Multilingual STT (Speech-to-Text):** Built with `faster-whisper` for fast local or server-side speech recognition.
- **Language Detection:** Identifies spoken English, Hindi, and Hinglish for tailored system prompt routing.
- **Cost-Aware Dynamic LLM Router:** Directs simple queries to cost-effective/fast models (Groq Llama 3) and complex reasoning to Gemini.
- **Property RAG (Retrieval-Augmented Generation):** Embedded property dataset in `ChromaDB` for accurate, context-aware property recommendations.
- **Telephony Integration:** Twilio voice webhook and WebSocket media streaming endpoint (`/twilio/voice`, `/twilio/stream`).
- **Lead Scoring & Storage:** SQLite database powered by SQLAlchemy for tracking caller leads and conversation transcripts.
- **Voice Output (TTS):** Dynamic speech generation using `gTTS` / Coqui TTS.

---

## 📁 Project Structure

```text
real-estate-voice-agent/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI entry point
│   ├── config.py             # Loads .env variables
│   ├── stt/
│   │   ├── __init__.py
│   │   └── transcriber.py    # Whisper STT logic
│   ├── tts/
│   │   ├── __init__.py
│   │   └── synthesizer.py    # gTTS / Coqui TTS logic
│   ├── language/
│   │   ├── __init__.py
│   │   └── detector.py       # Hindi/English/Hinglish detection
│   ├── router/
│   │   ├── __init__.py
│   │   └── llm_router.py     # Dynamic model routing logic
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embedder.py       # Embed property data into ChromaDB
│   │   └── retriever.py      # Semantic property search
│   ├── telephony/
│   │   ├── __init__.py
│   │   └── twilio_handler.py # Twilio call webhook handlers
│   ├── agent/
│   │   ├── __init__.py
│   │   └── conversation.py   # Conversation state + lead scoring
│   └── db/
│       ├── __init__.py
│       ├── models.py          # SQLite table definitions
│       └── crud.py            # DB read/write helpers
├── data/
│   └── properties.csv         # Mock property dataset (30 Indian listings)
├── tests/
│   └── test_stt.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Setup & Installation Instructions

### 1. Prerequisite
Ensure Python 3.10+ is installed on your system.

### 2. Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```ini
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number
```

---

## ⚡ Running the Application

Start the FastAPI development server with hot-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the API Documentation:
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc UI: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Running Tests

Execute pytest suite:
```bash
pytest
```
