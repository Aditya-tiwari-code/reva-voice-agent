import json
import uuid
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import init_db, get_db
from app.db import crud
from app.agent.conversation import ConversationAgent
from app.telephony.twilio_handler import router as twilio_router

# Global ConversationAgent Instance
agent_instance: Optional[ConversationAgent] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to handle startup and shutdown logic."""
    global agent_instance
    # 1. Initialize SQLite database tables
    init_db()
    
    # 2. Initialize Conversation Agent
    agent_instance = ConversationAgent()
    
    yield
    # Cleanup on shutdown if needed

app = FastAPI(
    title="REVA — Real Estate Voice Agent API",
    description="Cost-Aware Multilingual AI Voice Agent for Real Estate Lead Qualification",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for web frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Telephony Router
app.include_router(twilio_router)

# Serve Static Test UI Directory
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if not STATIC_DIR.exists():
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Pydantic Schemas
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    text: str
    phone: Optional[str] = None


# REST Endpoints
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0"}


@app.post("/chat/text")
async def chat_text(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Text-based query execution endpoint running full speech/RAG/LLM/scoring pipeline.
    """
    global agent_instance
    if not agent_instance:
        agent_instance = ConversationAgent()

    session_id = request.session_id or str(uuid.uuid4())

    # 1. Create or fetch lead in DB
    lead = crud.create_lead(db, session_id=session_id, phone=request.phone)

    # 2. Execute conversation agent pipeline
    result = agent_instance.process_text_input(session_id=session_id, user_text=request.text)

    # 3. Log conversation turn in DB
    crud.log_turn(db, session_id=session_id, turn_data=result)

    # 4. Update lead attributes and score in DB
    filters = result.get("filters_extracted", {})
    status = "escalated" if result.get("should_escalate") else ("qualified" if result["lead_score"] >= 60 else "new")
    
    crud.update_lead(
        db,
        session_id=session_id,
        location_pref=filters.get("city"),
        property_type=filters.get("property_type"),
        transaction_type=filters.get("transaction_type"),
        budget_lakh=filters.get("max_price"),
        lead_score=result["lead_score"],
        status=status
    )

    return result


@app.get("/leads")
async def get_leads(db: Session = Depends(get_db)):
    """Retrieve list of all lead qualification records."""
    leads = crud.get_all_leads(db)
    return leads


@app.get("/leads/{session_id}")
async def get_lead_detail(session_id: str, db: Session = Depends(get_db)):
    """Retrieve single lead detail by session_id."""
    lead = crud.get_lead_by_session(db, session_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead session not found.")
    return lead


@app.get("/leads/{session_id}/history")
async def get_lead_history(session_id: str, db: Session = Depends(get_db)):
    """Retrieve full multi-turn conversation dialogue history for a lead session."""
    turns = crud.get_turns_by_session(db, session_id)
    return turns


@app.get("/analytics/summary")
async def get_analytics(db: Session = Depends(get_db)):
    """Retrieve aggregated system analytics across calls, models, costs, and lead scores."""
    summary = crud.get_analytics_summary(db)
    return summary


# WebSocket Real-Time Chat Endpoint
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):
    """
    WebSocket endpoint enabling real-time streaming dialogue with REVA.
    """
    global agent_instance
    if not agent_instance:
        agent_instance = ConversationAgent()

    await websocket.accept()
    crud.create_lead(db, session_id=session_id)
    crud.create_call(db, session_id=session_id)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                payload = json.loads(raw_data)
                user_text = payload.get("text", "")
            except Exception:
                user_text = raw_data

            if not user_text.strip():
                continue

            # Run full pipeline
            result = agent_instance.process_text_input(session_id=session_id, user_text=user_text)

            # Log turn to DB
            crud.log_turn(db, session_id=session_id, turn_data=result)

            # Update Lead in DB
            status = "escalated" if result.get("should_escalate") else ("qualified" if result["lead_score"] >= 60 else "new")
            crud.update_lead(
                db,
                session_id=session_id,
                lead_score=result["lead_score"],
                status=status
            )

            # Stream result JSON back to WebSocket client
            await websocket.send_json(result)

    except WebSocketDisconnect:
        crud.end_call(db, session_id=session_id, outcome="completed")
    except Exception as e:
        crud.end_call(db, session_id=session_id, outcome="error")
        await websocket.close()


@app.get("/")
async def root():
    """Root homepage redirecting to Test Chat UI or API documentation."""
    test_html = STATIC_DIR / "test_chat.html"
    if test_html.exists():
        return FileResponse(str(test_html))
    return {"message": "Welcome to REVA Real Estate Voice Agent API", "docs": "/docs"}
