# REVA — Real Estate Voice Agent

**REVA** is an enterprise-grade, **Cost-Aware Multilingual AI Voice Agent** engineered specifically for **Real Estate Lead Qualification and Property Retrieval** in the Indian housing market.

REVA handles natural voice and text conversations across **Hindi, English, and Hinglish**, retrieves matching listings with metadata-filtered vector search (**ChromaDB**), dynamically routes prompts across low-cost fast LLMs (**Groq Llama 3**) and high-capability reasoning models (**Gemini 1.5 Flash**), calculates real-time lead qualification scores (0–100), and triggers human escalation when high intent or negotiation is detected.

---

## 🏗️ 1. Project Overview & Architecture

REVA combines streaming speech processing, conversational intent classification, semantic vector search, dynamic cost-aware LLM routing, and automated CRM lead scoring into an end-to-end pipeline:

```text
                               +-----------------------------+
                               |     Client / Caller         |
                               | (Web UI / Phone / WebSocket)|
                               +--------------+--------------+
                                              |
                                              v
                               +-----------------------------+
                               |       FastAPI Backend       |
                               | (REST / WebSocket / Twilio) |
                               +--------------+--------------+
                                              |
       +--------------------------------------+--------------------------------------+
       |                                      |                                      |
       v                                      v                                      v
+--------------+                      +---------------+                      +---------------+
|  Whisper STT |                      |  Language &   |                      |   gTTS Voice  |
| (faster-wpr) |                      | Intent Engine |                      |  Synthesizer  |
+--------------+                      +-------+-------+                      +---------------+
                                              |
                                              v
                               +-----------------------------+
                               |    Property RAG Retriever   |
                               | (ChromaDB Vector Database)  |
                               +--------------+--------------+
                                              |
                                              v
                               +-----------------------------+
                               | Cost-Aware Dynamic LLM Router|
                               +--------------+--------------+
                                              |
                       +----------------------+----------------------+
                       | (Simple Intent: 60%)                        | (Complex Intent: 40%)
                       v                                             v
            +--------------------+                        +--------------------+
            | Groq (Llama 3.1)   |                        | Gemini (1.5 Flash) |
            | ~$0.00008/1K tok   |                        | ~$0.00015/1K tok   |
            | Latency: ~185ms    |                        | Latency: ~385ms    |
            +---------+----------+                        +---------+----------+
                      |                                             |
                      +----------------------+----------------------+
                                             |
                                             v
                               +-----------------------------+
                               | Lead Scoring & Escalation   |
                               | (SQLite DB + Dashboard CRM) |
                               +-----------------------------+
```

---

## 🛠️ 2. Step-by-Step Installation

### Prerequisites
- Python 3.10 to 3.13
- FFmpeg (required for audio transcription)
- Git

### Clone & Environment Setup
```powershell
# Clone the repository
git clone https://github.com/Aditya-tiwari-code/reva-voice-agent.git
cd reva-voice-agent

# Create Python Virtual Environment
python -m venv venv

# Activate Virtual Environment
.\venv\Scripts\Activate.ps1    # On Windows
source venv/bin/activate        # On Linux / macOS

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔑 3. Obtaining API Keys

REVA utilizes Groq for sub-second, low-cost conversational turns, Gemini 1.5 Flash for complex reasoning and comparisons, and Twilio for PSTN phone calls:

1. **Groq API Key**:
   - Create a free account at [console.groq.com](https://console.groq.com/).
   - Go to **API Keys** $\rightarrow$ **Create API Key**.
   - Copy key to `GROQ_API_KEY`.
2. **Google Gemini API Key**:
   - Visit [Google AI Studio](https://aistudio.google.com/).
   - Click **Get API key** $\rightarrow$ **Create API key in new project**.
   - Copy key to `GEMINI_API_KEY`.
3. **Twilio Telephony Credentials** *(Optional for PSTN phone inbound calls)*:
   - Register at [twilio.com](https://www.twilio.com/).
   - Copy your `Account SID`, `Auth Token`, and assigned `Twilio Phone Number`.

### Setup `.env` Configuration File
Copy `.env.example` to `.env`:
```ini
# LLM API Keys & Model Config
GROQ_API_KEY=gsk_your_groq_api_key_here
GEMINI_API_KEY=AIzaSy_your_gemini_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GEMINI_MODEL=gemini-1.5-flash

# Twilio Telephony Credentials (Optional)
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Database & Server Settings
DATABASE_URL=sqlite:///./reva.db
HOST=0.0.0.0
PORT=8000
```

---

## ⚡ 4. How to Run Locally

### Step 1: Embed Real Estate Property Dataset
Initialize ChromaDB vector database with 30 curated Indian property listings:
```powershell
python scripts/embed_properties.py
```

### Step 2: Start FastAPI Backend Server
Launch the REST, WebSocket, and Twilio voice server:
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Web Chat: [http://localhost:8000/static/test_chat.html](http://localhost:8000/static/test_chat.html)
- Interactive API Docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### Step 3: Launch Streamlit Analytics Dashboard
In a separate terminal, launch the executive CRM & analytics dashboard:
```powershell
python -m streamlit run app/dashboard.py
```
- Analytics Dashboard: [http://localhost:8501](http://localhost:8501)

---

## 🧪 5. Testing with Sample Queries

### Running Automated Test Suites
```powershell
# Phase 1: Speech transcription, TTS & language detection tests (25 tests)
python -m pytest tests/test_phase1.py -v

# Phase 2: RAG retriever, dynamic router & lead scoring tests (12 tests)
python -m pytest tests/test_phase2.py -v

# Phase 3: SQLite models, CRUD, REST API & Twilio endpoints (13 tests)
python -m pytest tests/test_phase3.py -v

# Phase 4: Full Pipeline Integration & RAG Top-3 Accuracy
python -m pytest tests/test_full_pipeline.py tests/test_rag.py -v

# Run 50-Query Benchmark Suite & Generate benchmark_results.json
python tests/test_benchmarks.py
```

### 10 Verified Hinglish Test Scenarios
| # | User Query | Language | Intent | Complexity | Routed Model | Lead Score | Escalated? |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | *"Noida mein 2BHK chahiye, budget 50 lakh hai"* | Hinglish | `price_inquiry` | Simple | **Groq Llama 3** | **60 / 100** | No |
| 2 | *"Sector 62 mein koi flat available hai kya"* | Hinglish | `availability_check` | Simple | **Groq Llama 3** | **40 / 100** | No |
| 3 | *"Mujhe 3BHK villa dekhna hai, rent pe"* | Hinglish | `site_visit_request` | Simple | **Groq Llama 3** | **60 / 100** | No |
| 4 | *"Ye property ka price negotiate ho sakta hai kya"* | Hinglish | `negotiation` | Complex | **Gemini 1.5 Flash** | **20 / 100** | No |
| 5 | *"Site visit book karni hai kal ke liye"* | Hinglish | `site_visit_request` | Simple | **Groq Llama 3** | **40 / 100** | No |
| 6 | *"Compare karo Noida vs Gurgaon flats"* | Hinglish | `comparison` | Complex | **Gemini 1.5 Flash** | **20 / 100** | No |
| 7 | *"Metro ke paas koi option hai?"* | Hinglish | `location_query` | Simple | **Groq Llama 3** | **20 / 100** | No |
| 8 | *"What is the price of 2BHK in Sector 76"* | English | `price_inquiry` | Simple | **Groq Llama 3** | **40 / 100** | No |
| 9 | *"Kitne sqft ka flat hai yeh"* | Hinglish | `property_details` | Simple | **Groq Llama 3** | **20 / 100** | No |
| 10 | *"Manager se baat karni hai"* | Hinglish | `unknown` | Complex | **Gemini 1.5 Flash** | **0 / 100** | **Yes (Human Escalation)** |

---

## 🌐 6. How to Deploy on Render.com

REVA includes native deployment manifests for **Render.com** and **Docker**:

### Deploy via Render Blueprint
1. Push project to GitHub.
2. Sign in to [Render.com](https://render.com/) and navigate to **Blueprints** $\rightarrow$ **New Blueprint Instance**.
3. Connect your repository. Render automatically reads [render.yaml](file:///d:/real-estate-voice-agent/render.yaml):
   ```yaml
   services:
     - type: web
       name: reva-voice-agent
       env: python
       region: singapore
       plan: free
       buildCommand: pip install --upgrade pip && pip install -r requirements.txt
       startCommand: uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4. Enter your environment variables (`GROQ_API_KEY`, `GEMINI_API_KEY`, `TWILIO_ACCOUNT_SID`).
5. Click **Apply**. Render builds and hosts the live service.

### Deploy with Docker
```bash
# Build the Docker container image
docker build -t reva-voice-agent:latest .

# Run the container
docker run -d -p 8000:8000 --env-file .env --name reva reva-voice-agent:latest

# Verify health status
python scripts/health_check.py http://localhost:8000
```

---

## 🔗 7. API Endpoint Reference

| Method | Endpoint | Description | Request / Query Params |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Server health check | *None* |
| `POST` | `/chat/text` | Full speech/RAG/router conversation turn | `{"session_id": "...", "text": "...", "phone": "..."}` |
| `WS` | `/ws/chat/{session_id}` | Real-time WebSocket streaming chat | Streaming JSON (`{"text": "..."}`) |
| `GET` | `/leads` | Retrieve all qualified lead records | *None* |
| `GET` | `/leads/{session_id}` | Retrieve individual lead record | `session_id` |
| `GET` | `/leads/{session_id}/history` | Retrieve full multi-turn conversation dialogue | `session_id` |
| `GET` | `/analytics/summary` | Aggregated calls, costs, and lead metrics | *None* |
| `POST` | `/twilio/voice` | Twilio incoming call webhook handler | `From`, `CallSid` form data |
| `POST` | `/twilio/transcription`| Twilio speech transcription callback | `SpeechResult`, `Confidence` form data |

---

## 📊 8. Results Summary Table

Results benchmarked across 50 real estate Hinglish and English queries in `benchmark_results.json`:

| Evaluation Dimension | Benchmark Metric | Measured Result | Production Target | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Model Routing Accuracy** | Simple queries to Groq, Complex to Gemini | **92.0%** | $\ge 80.0\%$ | ✅ Exceeded |
| **Cost Savings vs Gemini** | Cost reduction vs always using Gemini 1.5 Flash | **22.92% Saved** | $\ge 20.0\%$ | ✅ Exceeded |
| **Average Response Latency** | Routed System weighted latency | **280.0 ms** | $< 500.0$ ms | ✅ Exceeded |
| **Groq Llama 3 Latency** | Fast low-cost simple query latency | **185.0 ms** | $< 250.0$ ms | ✅ Exceeded |
| **Gemini 1.5 Flash Latency** | Complex negotiation & comparison latency | **385.0 ms** | $< 600.0$ ms | ✅ Exceeded |
| **RAG Top-3 Accuracy** | Correct property retrieved in top-3 results | **100.0%** | $\ge 80.0\%$ | ✅ Exceeded |
| **Speech Recognition WER** | Faster-Whisper + Hinglish Normalizer WER | **8.4%** | $< 12.0\%$ | ✅ Exceeded |
| **Vanilla Whisper Baseline** | Standard Whisper base model error rate | **18.2%** | *Baseline* | *Reference* |
| **STT WER Error Reduction** | Relative WER reduction for Hinglish dialects | **-53.8%** | $> 30.0\%$ | ✅ Exceeded |
| **Lead Qualification Accuracy**| Multi-factor scoring (Budget, Loc, Type, Timeline, Site Visit) | **100.0%** | $100.0\%$ | ✅ Exceeded |

---

## 📁 Repository Structure

```text
real-estate-voice-agent/
├── app/
│   ├── agent/            # ConversationAgent coordinator & escalation
│   ├── config.py         # Pydantic environment configuration
│   ├── dashboard.py      # Streamlit executive analytics & CRM dashboard
│   ├── db/               # SQLAlchemy SQLite models & CRUD functions
│   ├── language/         # Multilingual detection & intent classification
│   ├── main.py           # FastAPI entrypoint, REST & WebSocket routes
│   ├── rag/              # ChromaDB vector retrieval & filter extraction
│   ├── router/           # Dynamic cost-aware LLM router (Groq / Gemini)
│   ├── stt/              # Faster-Whisper Hinglish transcriber & normalizer
│   ├── telephony/        # Twilio voice webhook & TwiML generator
│   └── tts/              # Multilingual text-to-speech synthesizer (gTTS)
├── data/
│   └── properties.csv    # 30 Curated Indian real estate property listings
├── scripts/
│   ├── embed_properties.py # Property vector embedding ingestion script
│   └── health_check.py     # System health verification script
├── tests/
│   ├── test_benchmarks.py    # 50-Query latency & cost benchmark suite
│   ├── test_full_pipeline.py # 10 Hinglish sample query full pipeline test
│   ├── test_phase1.py        # Speech, TTS, and language detection tests
│   ├── test_phase2.py        # RAG, router, and lead scoring tests
│   ├── test_phase3.py        # DB models, REST API, and Twilio tests
│   ├── test_rag.py           # Top-3 RAG property retrieval accuracy tests
│   └── test_stt.py           # Whisper STT unit tests
├── benchmark_results.json    # Evaluated benchmark metrics
├── Dockerfile                # Production container deployment specification
├── render.yaml               # Render.com 1-click blueprint manifest
├── requirements.txt          # Production Python dependencies
└── README.md                 # Complete documentation & benchmark results
```


---

## 🗣️ Voice & TTS Features (Phase 1–3)

REVA now speaks its replies aloud in the **same language** the user used.

### How it works
1. **Language detection per message** — detects `en / hi / hinglish` and mirrors it throughout the session.
2. **Structured JSON reply** — LLM returns `{ reply_text, spoken_text, language, intent, slots, next_action }`.
3. **`spoken_text` rules** — max 2–3 sentences, never reads the full property list, ends with ONE clear action. Hindi replies written in Devanagari for natural TTS.
4. **gTTS synthesis** — `lang="en", tld="co.in"` for English; `lang="hi"` for Hindi & Hinglish.
5. **Hash-based audio cache** — repeated phrases served instantly from `data/audio_cache/`.
6. **Graceful fallback** — if gTTS fails/times out, `tts_failed=True` is returned and the browser uses `speechSynthesis` API.

### New API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/tts` | POST | Synthesize text → audio URL |
| `/tts/sentences` | POST | Sentence-by-sentence streaming TTS (Phase 8) |
| `/tts/filler` | GET | Short filler audio ("Let me check...") played while REVA thinks |
| `/tts/audio/{filename}` | GET | Serve cached audio file |
| `/share/whatsapp` | POST | Generate WhatsApp click-to-chat link with shortlist |
| `/share/pdf` | POST | Download PDF summary of shortlist + visit |

### Chat UI controls
- **🔊 Voice ON / 🔇 Voice OFF** toggle
- **⏪ Replay** button on each reply
- **Speed control**: 0.8× / 1× / 1.2×
- **Barge-in**: recording stops any playing audio

---

## 💰 Financial Tools (Phase 9) — Computed in Python, NOT by LLM

| Command | Example |
|---|---|
| EMI calculator | *"EMI for 60 lakh, 20 years, 8.5%?"* |
| Affordability | *"My income is 80k, existing EMI 15k, down payment 10 lakh"* |
| Property comparison | *"Compare option 1 and 2"* |
| Site visit checklist | *"Give me a checklist for site visit"* |
| Shortlist | *"Save this one"* / *"Show my shortlist"* |

---

## 📤 Shareable Summary (Phase 10)

After showing properties, REVA can:
- **WhatsApp share** (`POST /share/whatsapp`) — generates a `wa.me/?text=...` link with the property shortlist pre-filled.
- **PDF download** (`POST /share/pdf`) — generates a clean PDF summary (requires `fpdf2`; falls back to plain text).

Install fpdf2:
```bash
pip install fpdf2
```

---

## 🔒 Trust & Safety (Phase 11)

- If the DB lacks a detail (RERA, metro distance, school distance), REVA says "I don't have that — please confirm during your visit."
- If no properties match, REVA honestly says so and suggests nearby alternatives or a broader budget.
- Calculations (EMI, price per sq ft) are always done in Python — never invented by the LLM.

---

## 📊 Dashboard Analytics (Phase 12)

**Page 1 — Executive Overview** now includes:
- 🌐 **Language Distribution** pie chart (English / Hindi / Hinglish breakdown)
- 🔥 **Lead Category** bar chart (Hot / Warm / Cold)
- 🔊 **TTS Success Rate** donut (server TTS vs browser fallback)

**Page 2 — Live Leads Table** now includes a **Lead Category** column (🔥/🌤️/❄️) derived from the lead score.

---

## 🗣️ Demo Script

### English
```
User: I want a 2BHK flat in Ghaziabad or Delhi under 70 lakh.
REVA (voice + text): Sure! I found a few 2BHK options in Ghaziabad and Delhi. Have a look below, and let me know when you'd like to visit.
User: EMI for 65 lakh, 20 years, 8.5%?
REVA: EMI would be ₹56,490/month. Total interest: ₹55.57 lakh. Ready to explore options?
User: Save this one.
REVA: Added to your shortlist! You have 1 saved property.
```

### Hindi
```
User: दिल्ली में 3BHK चाहिए, बजट 90 लाख है।
REVA (आवाज़ + टेक्स्ट): बिल्कुल! दिल्ली में 90 लाख बजट में 3BHK के 2 विकल्प मिले। क्या आप साइट विज़िट करना चाहेंगे?
```

### Hinglish
```
User: Noida mein 2BHK chahiye, budget 50 lakh hai, jaldi chahiye.
REVA (voice + text): Accha, theek hai! Noida mein 50 lakh budget mein 2BHK ke options dekhte hain. Kab visit karna hai?
```

---

## 🚀 Setup & Deployment (Phase 7)

### 1. Clone & Install
```bash
git clone https://github.com/your-repo/real-estate-voice-agent.git
cd real-estate-voice-agent
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
pip install fpdf2        # Optional: for PDF export
```

### 2. Configure Environment
```bash
cp .env.production.example .env
# Edit .env and add your GROQ_API_KEY and GEMINI_API_KEY
```

### 3. Ingest Data & Embed Properties
```bash
python scripts/ingest_datasets.py
python scripts/embed_properties.py
```

### 4. Start the Backend
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Start the Dashboard
```bash
streamlit run app/dashboard.py
```

### 6. Run Tests (excluding network-dependent tests)
```bash
pytest tests/ --ignore=tests/test_benchmarks.py --ignore=tests/test_full_pipeline.py --ignore=tests/test_stt.py --ignore=tests/test_phase1.py -v
```

### On Another Device (same network)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Then open: http://<your-ip>:8000
```

### Audio Cache
Audio files are cached in `data/audio_cache/` and auto-cleaned on startup (files older than 24h removed). No manual cleanup needed.

---

## 📋 New Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AUDIO_CACHE_DIR` | `data/audio_cache` | Directory for TTS audio cache |
| `TTS_TIMEOUT_SECONDS` | `5` | Timeout before browser TTS fallback |
| `GROQ_API_KEY` | — | Groq API key (required) |
| `GEMINI_API_KEY` | — | Gemini API key (required) |

