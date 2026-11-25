import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()
client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

print("Incoming numbers (webhook yahin set hota hai):")
nums = client.incoming_phone_numbers.list()
if not nums:
    print("  (koi nahi)")
for n in nums:
    print(" ", n.phone_number, "| voice:", n.capabilities.get("voice"), "| sms:", n.capabilities.get("sms"))

print("Verified caller IDs (tera apna number):")
ids = client.outgoing_caller_ids.list()
if not ids:
    print("  (koi nahi)")
for c in ids:
    print(" ", c.phone_number)