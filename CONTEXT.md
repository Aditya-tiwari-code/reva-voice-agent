# REVA — Real Estate Voice Agent: Project Context & Progress Documentation

---

## 📌 Executive Summary

**REVA (Real Estate Voice Agent)** is an enterprise-grade, **Cost-Aware Multilingual AI Voice & Chat Agent** engineered specifically for **Real Estate Lead Qualification and Property Retrieval** in the Indian market.

REVA handles inbound customer queries across **English, Hindi, and Hinglish**, retrieves semantically matching property listings from a vector database (**ChromaDB**), dynamically routes prompts across budget-friendly fast LLMs (**Groq Llama 3**) and high-capability reasoning models (**Gemini 1.5 Flash**), calculates real-time lead qualification scores (0–100), and handles human agent escalation.

---

## 🛠️ Technology Stack

- **Programming Language:** Python 3.10+
- **Backend Framework:** FastAPI (REST + WebSockets + Static File Hosting)
- **Analytics & Dashboard:** Streamlit + Plotly + Pandas
- **Database & Storage:**
  - **Relational DB:** SQLite powered by SQLAlchemy (`leads`, `calls`, `conversation_turns`)
  - **Vector DB:** ChromaDB persistent store with `SentenceTransformer("all-MiniLM-L6-v2")` embeddings
- **Speech & Audio Pipeline:**
  - **STT (Speech-to-Text):** `faster-whisper` (int8 quantized local execution)
  - **TTS (Text-to-Speech):** `gTTS` (supporting `hi` and `en` voice synthesis)
- **Language & Intent Processing:** `langdetect` + Custom regex pattern matcher for Hindi/English/Hinglish and 9 real estate intent categories.
- **Dynamic LLM Router:**
  - **Simple Queries:** Groq (`llama3-8b-8192`) — ~$0.00008 / 1K tokens
  - **Complex Queries:** Google Gemini (`gemini-1.5-flash`) — ~$0.00015 / 1K tokens
- **Telephony Integration:** Twilio Voice Webhooks & TwiML generator.
- **Deployment & Containerization:** Dockerfile, `render.yaml` (Render.com), `health_check.py`.

---

## 📁 Repository Structure

```text
real-estate-voice-agent/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI entry point, REST APIs, WebSockets & lifespan setup
│   ├── config.py             # Loads .env configurations via python-dotenv
│   ├── dashboard.py          # Streamlit 3-page Analytics & CRM Dashboard
│   ├── stt/
│   │   ├── __init__.py
│   │   └── transcriber.py    # HinglishTranscriber with faster-whisper & text normalization
│   ├── tts/
│   │   ├── __init__.py
│   │   └── synthesizer.py    # MultilingualSynthesizer using gTTS for MP3 & byte streaming
│   ├── language/
│   │   ├── __init__.py
│   │   └── detector.py       # LanguageDetector for Hindi/English/Hinglish & intent classification
│   ├── router/
│   │   ├── __init__.py
│   │   └── llm_router.py     # AdaptiveLLMRouter for Groq Llama 3 vs Gemini Flash routing
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embedder.py       # PropertyEmbedder to index CSV listings into ChromaDB
│   │   └── retriever.py      # PropertyRetriever for metadata extraction & semantic vector search
│   ├── telephony/
│   │   ├── __init__.py
│   │   └── twilio_handler.py # TwilioHandler for TwiML responses & voice webhooks
│   ├── agent/
│   │   ├── __init__.py
│   │   └── conversation.py   # ConversationAgent for multi-turn flow, lead scoring & human escalation
│   └── db/
│       ├── __init__.py
│       ├── models.py          # SQLAlchemy models (Lead, Call, ConversationTurn)
│       └── crud.py            # Helper functions for database operations & analytics summary
├── data/
│   └── properties.csv         # 30 realistic Indian real estate listings dataset
├── static/
│   └── test_chat.html         # Real-time WebSocket chat UI with score badge & metadata
├── scripts/
│   ├── embed_properties.py    # Standalone ingestion script to index CSV into ChromaDB
│   └── health_check.py        # Health check script for server monitoring
├── tests/
│   ├── __init__.py
│   ├── test_phase1.py         # 25 unit tests for Speech & Language modules
│   ├── test_phase2.py         # 12 unit tests for RAG, Router & Scoring modules
│   ├── test_phase3.py         # 13 integration tests for DB, REST APIs, Twilio & Escalation
│   ├── test_full_pipeline.py  # 10 Hinglish queries + RAG retrieval accuracy test
│   └── test_benchmarks.py     # 50-query benchmark suite measuring cost & latency
├── benchmark_results.json    # Generated system benchmark summary
├── Dockerfile                # Production Docker container configuration
├── render.yaml               # 1-click Render.com deployment manifest
├── .env.example              # Development environment variables
├── .env.production.example   # Production environment template
├── requirements.txt          # Python package dependencies
├── CONTEXT.md                # Complete project context & status documentation
└── README.md                 # Complete documentation & setup instructions
```

---

## 🚀 All Phased Implementations Complete

### ✅ Phase 1: Speech Pipeline
- `HinglishTranscriber` (`faster-whisper`), `LanguageDetector` (Hindi/English/Hinglish + 9 intents), `MultilingualSynthesizer` (`gTTS`).
- **25/25 Pytest unit tests passed.**

### ✅ Phase 2: Core AI Development
- `PropertyEmbedder` & `PropertyRetriever` (ChromaDB + SentenceTransformers), `AdaptiveLLMRouter` (Groq Llama 3 vs Gemini Flash), `ConversationAgent` (0–100 lead scoring).
- **12/12 Pytest unit tests passed.**

### ✅ Phase 3: System Integration
- SQLite DB (`Lead`, `Call`, `ConversationTurn`), FastAPI REST & WebSockets backend (`main.py`), Twilio webhooks (`twilio_handler.py`), Human Escalation (`should_escalate`), Glassmorphism Web Interface (`static/test_chat.html`).
- **13/13 Pytest integration tests passed.**

### ✅ Phase 4: Testing, Benchmarking, Dashboard & Deployment
- **Full Pipeline & RAG Accuracy Tests (`test_full_pipeline.py`)**: 10 sample Hinglish queries + RAG top-3 retrieval accuracy (100% pass).
- **Benchmark Suite (`test_benchmarks.py`)**: 50 queries evaluated $\rightarrow$ **92% routing accuracy**, **28.31% cost savings vs always-using Gemini**, average routed latency **1.29s**. Saved to `benchmark_results.json`.
- **Streamlit Analytics Dashboard (`app/dashboard.py`)**: 3-page interactive dashboard (Overview, Live Leads CRM Table, System Benchmarks).
- **Deployment Artifacts**: `Dockerfile`, `render.yaml`, `.env.production.example`, `scripts/health_check.py`.
- **Comprehensive Documentation**: Complete `README.md` with architecture, setup, API reference, benchmark metrics, and Render.com deployment guide.

---

## 📊 Benchmark Summary Metrics (`benchmark_results.json`)

```json
{
  "total_queries_tested": 50,
  "avg_routed_latency_ms": 1296.66,
  "avg_groq_latency_ms": 907.66,
  "avg_gemini_latency_ms": 1815.32,
  "total_routed_cost_usd": 0.001469,
  "total_always_gemini_cost_usd": 0.002049,
  "cost_saved_usd": 0.00058,
  "cost_savings_percent": 28.31,
  "routing_accuracy_percent": 92.0
}
```
