"""
set_twilio_webhook.py
─────────────────────
Sets the Voice webhook URL on a Twilio phone number.

Usage (from project root, inside venv):
    python scripts/set_twilio_webhook.py

Required environment variables (loaded from .env):
    TWILIO_ACCOUNT_SID   – Twilio Account SID (starts with AC…)
    TWILIO_AUTH_TOKEN    – Twilio Auth Token
    TWILIO_PHONE_NUMBER  – E.164 phone number, e.g. +17372324091
    PUBLIC_BASE_URL      – Public HTTPS base URL, e.g. https://xxx.ngrok-free.dev
"""

import sys
import os
from dotenv import load_dotenv

# ── Load .env ──────────────────────────────────────────────────────────────────
load_dotenv()

# ── Read & validate required environment variables ────────────────────────────
missing = []

ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN")
PHONE_NUMBER  = os.getenv("TWILIO_PHONE_NUMBER")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")

if not ACCOUNT_SID:
    missing.append("TWILIO_ACCOUNT_SID")
if not AUTH_TOKEN:
    missing.append("TWILIO_AUTH_TOKEN")
if not PHONE_NUMBER:
    missing.append("TWILIO_PHONE_NUMBER")
if not PUBLIC_BASE_URL:
    missing.append("PUBLIC_BASE_URL")

if missing:
    print(
        f"Error: The following required environment variable(s) are missing or empty:\n"
        f"  {', '.join(missing)}\n\n"
        f"Set them in your .env file (see .env.example) and try again.",
        file=sys.stderr,
    )
    sys.exit(1)

# Strip any trailing slash from the base URL so the path is always clean.
PUBLIC_BASE_URL = PUBLIC_BASE_URL.rstrip("/")
VOICE_URL = f"{PUBLIC_BASE_URL}/twilio/voice"

# ── Import Twilio SDK ──────────────────────────────────────────────────────────
try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
except ImportError:
    print(
        "Error: The 'twilio' package is not installed.\n"
        "Install it with:  pip install twilio",
        file=sys.stderr,
    )
    sys.exit(1)

# ── Build client ───────────────────────────────────────────────────────────────
try:
    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    # ── Look up the phone number in this account ───────────────────────────────
    numbers = client.incoming_phone_numbers.list(phone_number=PHONE_NUMBER)

    if not numbers:
        print(
            f"Error: Phone number {PHONE_NUMBER!r} was not found under account "
            f"{ACCOUNT_SID!r}.\n"
            f"Check that TWILIO_PHONE_NUMBER matches a number in your Twilio account.",
            file=sys.stderr,
        )
        sys.exit(1)

    phone_number_resource = numbers[0]

    # ── Update the Voice webhook ───────────────────────────────────────────────
    updated = phone_number_resource.update(
        voice_url=VOICE_URL,
        voice_method="POST",
    )

    print(f"Done: {updated.phone_number} -> {updated.voice_url}")

except TwilioRestException as exc:
    # HTTP 401 → bad credentials
    if exc.status == 401:
        print(
            "Error: Authentication failed (HTTP 401).\n"
            "Double-check that TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are correct.",
            file=sys.stderr,
        )
    else:
        print(f"Error: Twilio API returned an error: {exc}", file=sys.stderr)
    sys.exit(1)

