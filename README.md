# REVA — Real Estate Voice Agent

**REVA** is a **Cost-Aware Multilingual AI Voice Agent** designed specifically for **Real Estate Lead Qualification and Property Retrieval** in the Indian market.

REVA handles voice and text queries across **Hindi, English, and Hinglish**, retrieves matching properties using vector search (**ChromaDB**), dynamically routes prompts across low-cost fast LLMs (**Groq Llama 3**) and high-capability reasoning models (**Gemini 1.5 Flash**), and calculates real-time lead qualification scores with human escalation triggers.

---

## 🏗️ System Architecture

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
|  Whisper STT |                      | Language &    |                      |   gTTS Voice  |
| (faster-wpr) |                      | Intent Engine |                      |   Synthesizer |
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
                       | (Simple Intent)                             | (Complex Intent)
                       v                                             v
            +--------------------+                        +--------------------+
            | Groq (Llama3-8b)   |                        | Gemini (1.5 Flash) |
            | ~$0.00008/1K tok   |                        | ~$0.00015/1K tok   |
            +---------+----------+                        +---------+----------+
                      |                                             |
                      +----------------------+----------------------+
                                             |
                                             v
                               +-----------------------------+
                               | Lead Scoring & Escalation   |
                               | (SQLite DB + Analytics UI)  |
                               +-----------------------------+
```

---

## 📦 Key Features

- **Multilingual Speech & Text Processing**: Native STT & TTS supporting Hindi, English, and Hinglish.
- **Semantic Property RAG**: Ingests 30+ property listings with metadata-filtered vector search (City, BHK, Budget, Property Type).
- **Cost-Aware Model Routing**: 92% routing accuracy sending simple queries to Groq and complex negotiation/comparisons to Gemini.
- **Automated Lead Scoring**: Real-time score (0–100) tracking customer budget, location, timeline, property preference, and site visit request intent.
- **Human Agent Escalation**: Automatically flags high-value leads ($\ge 80$ score), repeated negotiation attempts, or explicit requests for human transfer.
- **Streamlit Analytics Dashboard**: Executive KPIs, live CRM leads table, and system benchmarking suite.

---

## 🛠️ Step-by-Step Installation

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Clone Repository & Setup Virtual Environment
```powershell
git clone https://github.com/Aditya-tiwari-code/reva-voice-agent.git
cd reva-voice-agent

# Create & Activate Virtual Environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # On Windows
source venv/bin/activate       # On Linux/macOS
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔑 Obtaining API Keys

1. **Groq API Key**:
   - Register at [console.groq.com](https://console.groq.com/)
   - Navigate to API Keys $\rightarrow$ Create API Key.
2. **Gemini API Key**:
   - Register at [aistudio.google.com](https://aistudio.google.com/)
   - Click "Get API key" $\rightarrow$ Create API key in new project.
3. **Twilio Credentials** *(Optional for Telephony)*:
   - Register at [twilio.com](https://www.twilio.com/)
   - Copy Account SID, Auth Token, and Active Phone Number from Console.

Create `.env` in project root:
```ini
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_phone
DATABASE_URL=sqlite:///./reva.db
HOST=0.0.0.0
PORT=8000
```

---

## ⚡ Local Execution & Running REVA

### 1. Embed Property Dataset into Vector DB
```powershell
python scripts/embed_properties.py
```

### 2. Launch FastAPI Server
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Access Chat Web Interface: **[http://localhost:8000/static/test_chat.html](http://localhost:8000/static/test_chat.html)**
- Access Swagger Documentation: **[http://localhost:8000/docs](http://localhost:8000/docs)**

### 3. Launch Streamlit Analytics Dashboard
```powershell
python -m streamlit run app/dashboard.py
```
- Access Dashboard: **[http://localhost:8501](http://localhost:8501)**

---

## 🧪 Testing Suite & Benchmarking

Run the complete test suite across all 4 project phases:

```powershell
# Phase 1: Speech & Language Pipeline Tests (25 tests)
python -m pytest tests/test_phase1.py -v

# Phase 2: RAG, Router & Scoring Tests (12 tests)
python -m pytest tests/test_phase2.py -v

# Phase 3: DB, REST APIs, Twilio & Escalation Tests (13 tests)
python -m pytest tests/test_phase3.py -v

# Phase 4: Full End-to-End Pipeline & RAG Accuracy
python -m pytest tests/test_full_pipeline.py -v

# Run 50-Query System Benchmarks & Generate benchmark_results.json
python tests/test_benchmarks.py
```

---

## 📊 System Benchmark Results Summary

| Metric | Result | Target Benchmark |
| :--- | :---: | :---: |
| **Total Queries Evaluated** | **50** | 50 |
| **Routing Accuracy** | **92.0%** | $\ge 80\%$ |
| **Cost Reduction vs Always-Gemini** | **28.31% Saved** | $\ge 20\%$ |
| **Avg Routed Response Latency** | **1,296 ms** | $< 2,000$ ms |
| **RAG Retrieval Accuracy (Top 3)** | **100.0%** | $\ge 80\%$ |
| **Lead Scoring Accuracy** | **100.0%** | 100% |

---

## 🌐 Deploying on Render.com

REVA includes a pre-configured `render.yaml` for 1-click deployment on Render.com free tier:

1. Push code to GitHub repository.
2. Log into [Render.com](https://render.com/) and click **New +** $\rightarrow$ **Blueprint**.
3. Connect your `reva-voice-agent` repository.
4. Set environment variables (`GROQ_API_KEY`, `GEMINI_API_KEY`).
5. Click **Apply**. Render will auto-build and deploy your web service!

Or use Docker:
```bash
docker build -t reva-voice-agent .
docker run -p 8000:8000 --env-file .env reva-voice-agent
```

---

## 🔗 API Endpoint Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | System health check (`{"status": "ok"}`) |
| `POST` | `/chat/text` | Runs full AI RAG pipeline for text input |
| `WS` | `/ws/chat/{session_id}` | Real-time WebSocket streaming endpoint |
| `GET` | `/leads` | Fetches all qualified lead records |
| `GET` | `/leads/{session_id}` | Fetches detailed lead profile |
| `GET` | `/analytics/summary` | Aggregated analytics & model statistics |
| `POST` | `/twilio/voice` | Twilio incoming call TwiML webhook |
| `POST` | `/twilio/transcription` | Twilio speech callback webhook |
