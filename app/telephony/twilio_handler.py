import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response, JSONResponse

router = APIRouter(prefix="/twilio", tags=["telephony"])

# ── Twilio credentials check ──────────────────────────────────────────────────
# If the credentials are missing or still contain placeholder text, every
# /twilio/* endpoint returns HTTP 503 instead of crashing.

_PLACEHOLDER_TOKENS = {"", "your_twilio_account_sid_here", "your_twilio_auth_token_here"}

def _twilio_configured() -> bool:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    tok = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    return (sid not in _PLACEHOLDER_TOKENS) and (tok not in _PLACEHOLDER_TOKENS)

_NOT_CONFIGURED_RESPONSE = JSONResponse(
    status_code=503,
    content={"error": "Twilio not configured", "detail": "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env to enable telephony."}
)


class TwilioHandler:
    """
    Generates TwiML XML responses for Twilio Voice Webhooks and call handling.
    """

    def generate_greeting_twiml(self, language: str = "hinglish") -> str:
        """
        Generates initial greeting TwiML XML and gathers caller speech input.
        """
        greeting = "Namaste! Main REVA hoon, aapki real estate assistant. Aap kya dhundh rahe hain?"
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="hi-IN">{greeting}</Say>
    <Gather input="speech" timeout="5" speechTimeout="2" action="/twilio/transcription" method="POST">
        <Say voice="Polly.Aditi" language="hi-IN">Kripya boliye, aapko kis tarah ki property chahiye?</Say>
    </Gather>
    <Say voice="Polly.Aditi" language="hi-IN">Koi aawaz nahi sunai di. Dhanyawad.</Say>
</Response>"""
        return twiml

    def generate_response_twiml(self, response_text: str, language: str = "hinglish") -> str:
        """
        Generates response TwiML XML speaking AI answer and gathering next speech input.
        """
        lang_code = "hi-IN" if language in ["hindi", "hinglish"] else "en-IN"
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="{lang_code}">{response_text}</Say>
    <Gather input="speech" timeout="5" speechTimeout="2" action="/twilio/transcription" method="POST">
    </Gather>
</Response>"""
        return twiml

    def generate_escalation_twiml(self, agent_phone: str = "+18005550199") -> str:
        """
        Generates escalation TwiML transferring the caller to a human agent.
        """
        message = "Main aapko hamari team se connect kar raha hoon. Ek minute please."
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="hi-IN">{message}</Say>
    <Dial>{agent_phone}</Dial>
</Response>"""
        return twiml

    def generate_booking_twiml(self, property_name: str, date: str) -> str:
        """
        Generates confirmation TwiML for site visit booking.
        """
        message = f"Aapka site visit {property_name} ke liye {date} ko book ho gaya hai. Hamari team aapko contact karegi. Dhanyawad!"
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="hi-IN">{message}</Say>
</Response>"""
        return twiml


# Twilio Webhook API Endpoints
twilio_handler = TwilioHandler()

@router.post("/voice")
async def handle_incoming_voice(request: Request):
    """
    Twilio voice webhook triggered when a new call arrives.
    Returns HTTP 503 if Twilio credentials are not configured.
    """
    if not _twilio_configured():
        return _NOT_CONFIGURED_RESPONSE
    twiml_xml = twilio_handler.generate_greeting_twiml()
    return Response(content=twiml_xml, media_type="text/xml")

@router.post("/transcription")
async def handle_voice_transcription(
    SpeechResult: str = Form(default=""),
    CallSid: str = Form(default="default_session")
):
    """
    Twilio callback receiving gathered speech text input.
    Returns HTTP 503 if Twilio credentials are not configured.
    """
    if not _twilio_configured():
        return _NOT_CONFIGURED_RESPONSE

    if not SpeechResult:
        twiml = twilio_handler.generate_response_twiml("Aapki aawaz saaf nahi aayi. Kripya dobara bataiye.")
        return Response(content=twiml, media_type="text/xml")

    # In production, pass SpeechResult to ConversationAgent
    response_text = f"Samajh gaya. Aapne pucha: '{SpeechResult}'. Hum offers dhoondh rahe hain."
    twiml = twilio_handler.generate_response_twiml(response_text)
    return Response(content=twiml, media_type="text/xml")

