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
from app.tts.tts_service import tts_service, AUDIO_CACHE_DIR, cleanup_old_audio_files

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

    # 3. Phase 7: Audio cache cleanup on startup (remove files older than 24h)
    cleanup_old_audio_files(AUDIO_CACHE_DIR, max_age_hours=24)
    
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


class BookingRequest(BaseModel):
    name: str
    phone: str
    property_id: Optional[str] = None
    preferred_date: str
    preferred_time: str
    session_id: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "english"


# REST Endpoints
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0"}


@app.post(\"/tts\")
async def generate_tts(request: TTSRequest):
    """
    Synthesize text to speech using gTTS with Indian accents and audio cache.
    Degrades gracefully returning tts_failed=True if synthesis fails.
    """
    res = tts_service.generate_speech(text=request.text, language=request.language or "english")
    return res


@app.post("/tts/sentences")
async def generate_tts_sentences(request: TTSRequest):
    """
    Phase 8: Sentence-by-sentence streaming TTS.
    Returns a list of audio URLs per sentence so the browser can play
    the first sentence while the rest are still loading.
    """
    sentences = tts_service.generate_speech_sentences(
        text=request.text,
        language=request.language or "english"
    )
    return {"sentences": sentences}


@app.get("/tts/filler")
async def get_filler_audio(language: str = "english"):
    """
    Phase 8: Return a short filler audio played immediately while REVA thinks.
    """
    result = tts_service.get_filler_audio(language=language)
    return result


@app.get("/tts/audio/{filename}")
async def get_tts_audio_file(filename: str):
    """Stream cached synthesized audio file."""
    # Prevent directory traversal
    clean_filename = Path(filename).name
    file_path = AUDIO_CACHE_DIR / clean_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(str(file_path), media_type="audio/mpeg")


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


@app.post("/bookings")
async def create_booking(request: BookingRequest, db: Session = Depends(get_db)):
    """
    Book a property site visit.
    Validates phone number, creates site_visit record in SQLite,
    updates lead status to 'booked', and returns confirmation.
    """
    import re
    phone_clean = re.sub(r'[\s\-\(\)\+]', '', request.phone)
    if not phone_clean.isdigit() or len(phone_clean) < 10 or len(phone_clean) > 15:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number. Please provide a valid 10-digit mobile number."
        )

    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Name is required for booking.")
    if not request.preferred_date.strip():
        raise HTTPException(status_code=400, detail="Preferred date is required.")
    if not request.preferred_time.strip():
        raise HTTPException(status_code=400, detail="Preferred time is required.")

    visit = crud.create_site_visit(
        db=db,
        name=request.name,
        phone=request.phone,
        property_id=request.property_id,
        preferred_date=request.preferred_date,
        preferred_time=request.preferred_time,
        session_id=request.session_id
    )

    return {
        "status": "success",
        "message": f"Site visit confirmed for {visit.name} on {visit.preferred_date} at {visit.preferred_time}.",
        "booking": {
            "id": visit.id,
            "name": visit.name,
            "phone": visit.phone,
            "property_id": visit.property_id,
            "preferred_date": visit.preferred_date,
            "preferred_time": visit.preferred_time,
            "session_id": visit.session_id,
            "status": visit.status,
            "created_at": str(visit.created_at)
        }
    }


@app.get("/bookings")
async def get_bookings(db: Session = Depends(get_db)):
    """Retrieve all site visit bookings for dashboard and administrative review."""
    visits = crud.get_all_site_visits(db)
    return visits


@app.get("/properties/featured")
async def get_featured_properties():
    """Retrieve featured listings for homepage showcase."""
    import csv
    csv_path = Path(__file__).resolve().parent.parent / "data" / "properties.csv"
    featured = []
    if csv_path.exists():
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # Pick a diverse mix of 6 featured properties across cities and buy/rent
            for row in reader:
                pid = int(row.get("id", 0))
                if pid in [2, 4, 10, 31, 33, 38]:  # Bangalore, Noida, Mumbai rent, Ghaziabad buy, Ghaziabad rent, Noida rent
                    featured.append({
                        "id": pid,
                        "title": row.get("title", ""),
                        "location": row.get("location", ""),
                        "city": row.get("city", ""),
                        "price_lakh": float(row.get("price_lakh", 0.0)),
                        "bhk": int(row.get("bhk", 0)),
                        "area_sqft": int(row.get("area_sqft", 0)),
                        "property_type": row.get("property_type", "Apartment"),
                        "transaction_type": row.get("transaction_type", "buy"),
                        "availability": row.get("availability", "Ready to Move"),
                        "amenities": row.get("amenities", ""),
                        "description": row.get("description", "")
                    })
    return featured


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
    """Root homepage serving index.html or fallback to test_chat.html."""
    index_html = STATIC_DIR / "index.html"
    if index_html.exists():
        return FileResponse(str(index_html))
    test_html = STATIC_DIR / "test_chat.html"
    if test_html.exists():
        return FileResponse(str(test_html))
    return {"message": "Welcome to REVA Real Estate Voice Agent API", "docs": "/docs"}


# ==========================================
# Phase 10: Shareable Summary Endpoints
# ==========================================
class ShareSummaryRequest(BaseModel):
    session_id: Optional[str] = None
    shortlist: list = []
    visit_date: Optional[str] = None
    visit_time: Optional[str] = None
    name: Optional[str] = None


@app.post("/share/whatsapp")
async def generate_whatsapp_link(request: ShareSummaryRequest):
    """
    Phase 10: Generate a WhatsApp click-to-chat link with pre-filled property shortlist summary.
    Uses wa.me/?text= with URL-encoded plain text — no Twilio needed.
    """
    import urllib.parse
    lines = ["🏠 *REVA Property Shortlist*\n"]
    for i, prop in enumerate(request.shortlist, 1):
        name_ = prop.get("title") or "Property"
        city = prop.get("city") or ""
        price = prop.get("price_lakh", "")
        bhk = prop.get("bhk", "")
        area = prop.get("area_sqft", "")
        lines.append(
            f"{i}. *{name_}* — {bhk}BHK, {city}\n"
            f"   💰 ₹{price} Lakh | 📐 {area} sq ft\n"
        )
    if request.visit_date and request.visit_time:
        lines.append(f"\n📅 *Site Visit Booked:* {request.visit_date} at {request.visit_time}")
    if request.name:
        lines.append(f"👤 Name: {request.name}")
    lines.append("\n_Sent via REVA — Real Estate Voice Agent_")
    full_text = "\n".join(lines)
    encoded = urllib.parse.quote(full_text)
    wa_link = f"https://wa.me/?text={encoded}"
    return {"whatsapp_url": wa_link, "summary_text": full_text}


@app.post("/share/pdf")
async def generate_pdf_summary(request: ShareSummaryRequest):
    """
    Phase 10: Generate a downloadable PDF summary of the property shortlist and visit booking.
    Uses fpdf2 (pure-Python, no LaTeX). Falls back to plain text if fpdf2 not installed.
    """
    from fastapi.responses import Response
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=16)
        pdf.cell(0, 12, "REVA Property Shortlist Summary", ln=True, align="C")
        pdf.ln(4)
        pdf.set_font("Helvetica", size=11)

        for i, prop in enumerate(request.shortlist, 1):
            name_ = prop.get("title") or "Property"
            city = prop.get("city") or ""
            price = prop.get("price_lakh", "")
            bhk = prop.get("bhk", "")
            area = prop.get("area_sqft", "")
            avail = prop.get("availability", "Ready to Move")
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.cell(0, 8, f"{i}. {name_}", ln=True)
            pdf.set_font("Helvetica", size=10)
            pdf.cell(0, 7, f"   {bhk}BHK | {city} | Rs {price} Lakh | {area} sq ft | {avail}", ln=True)
            pdf.ln(2)

        if request.visit_date and request.visit_time:
            pdf.ln(4)
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.cell(0, 8, f"Site Visit: {request.visit_date} at {request.visit_time}", ln=True)

        pdf.ln(6)
        pdf.set_font("Helvetica", style="I", size=9)
        pdf.cell(0, 7, "Generated by REVA - Real Estate Voice Agent", ln=True, align="C")
        pdf.cell(0, 7, "Note: Prices are indicative. Confirm all details during your site visit.", ln=True, align="C")

        pdf_bytes = pdf.output()
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=reva_shortlist.pdf"}
        )
    except ImportError:
        # Graceful fallback: return plain text
        lines = ["REVA Property Shortlist Summary\n"]
        for i, prop in enumerate(request.shortlist, 1):
            lines.append(f"{i}. {prop.get('title')} — {prop.get('bhk')}BHK {prop.get('city')} Rs {prop.get('price_lakh')} Lakh")
        if request.visit_date:
            lines.append(f"\nSite Visit: {request.visit_date} at {request.visit_time}")
        return Response(
            content="\n".join(lines),
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=reva_shortlist.txt"}
        )
