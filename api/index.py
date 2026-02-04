import re
import logging
import random
import requests
import os
from typing import List, Optional, Dict
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

# =========================================================
# 1. SETUP & CONFIGURATION
# =========================================================
app = FastAPI(title="GUVI Zombie HoneyPot")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ZombieAgent")

# HACKATHON CONFIG
# In Vercel, set these in the "Environment Variables" section of your dashboard
CALLBACK_URL = os.environ.get("CALLBACK_URL", "https://hackathon.guvi.in/api/updateHoneyPotFinalResult")
SECRET_API_KEY = os.environ.get("SECRET_API_KEY", "YOUR_SECRET_API_KEY_HERE") 

# =========================================================
# 2. THE "ZOMBIE" BRAIN (Message Generator)
# =========================================================
ZOMBIE_MEMORY = {
    "intros": [
        "Hello sir,", "Excuse me,", "Oh my god,", "Wait,", "Listen,", 
        "Actually,", "One second,", "Sir/Madam,", "I am confused,", 
        "My phone is slow but,", "Sorry for delay,", "I am reading this,",
        "Okay I understand but,", "Just a moment,", "Hold on,", "Tech is hard for me,",
        "My glasses were missing,", "My grandson is not here so,", "Please help me,"
    ],
    "upi": [
        "my GPay is showing 'Server Error' red circle.",
        "PhonePe is asking for my PIN but screen is black.",
        "I typed the amount but button is grey.",
        "Paytm says 'KYC pending' suddenly.",
        "is this a Merchant account? It asks me.",
        "can I send 10 rupees first to check?",
        "the QR code is not scanning clearly.",
        "my bank server is down I think.",
        "it says 'Payment Declined' but money is gone?",
        "do I enter PIN on the incoming request?"
    ],
    "bank": [
        "I cannot find my passbook number.",
        "is this for my SBI or HDFC account?",
        "the IFSC code you gave is showing invalid.",
        "manager said never share OTP on call.",
        "my ATM card is broken actually.",
        "can I go to the branch and do this?",
        "internet banking is locked, wait.",
        "I am scared to lose my pension money.",
        "is there a charge for this transfer?",
        "my account balance is showing zero?"
    ],
    "link": [
        "the blue link is not opening.",
        "my phone says 'Malware Detected' when I click.",
        "screen went white after clicking.",
        "it is asking to download an APK file?",
        "chrome is blocking this site.",
        "can you send the link again properly?",
        "it redirected to a betting site I think.",
        "do I need to update my browser first?",
        "the website text is very small.",
        "is this the official gov portal?"
    ],
    "otp": [
        "I did not receive any 6 digit code.",
        "message came but it is in different language.",
        "wait, the timer ran out. Send again.",
        "is the code 4566 or 4576? blurry screen.",
        "I deleted the message by mistake.",
        "my son told me not to share codes.",
        "phone battery died, just restarted.",
        "I am looking at messages, wait.",
        "why is the code from a personal number?",
        "it says 'Do not share with anyone'."
    ],
    "threat": [
        "please do not block my account sir.",
        "I am trying my best, don't be angry.",
        "will police come to my house?",
        "I am an old man, have mercy.",
        "why are you shouting in messages?",
        "give me 5 minutes, panic attack.",
        "is this legal? I am worried.",
        "my heart rate is going up.",
        "can we do this tomorrow please?",
        "I promise to pay, just wait."
    ],
    "generic": [
        "I don't understand this tech stuff.",
        "what do I do next?",
        "is this real or fake?",
        "how do I get the prize money?",
        "guide me step by step please.",
        "screen is frozen.",
        "typing is very hard for me.",
        "network is 1 bar only.",
        "battery is 2 percent.",
        "who is this speaking?"
    ],
    "delays": [
        "Let me find my charger.", "Someone is at the door.", 
        "Going to balcony for signal.", "Asking my neighbor for help.",
        "Restarting my phone wait.", "Wait, searching for glasses.",
        "Hold on, internet buffering.", "Just one minute please.",
        "Don't cut the call/chat.", "Let me write this down."
    ],
    "closers": [
        "Are you there?", "Hello?", "Reply fast.", 
        "Did you get that?", "Can you hear me?", 
        "Waiting for you.", "Please reply.", 
        "It is loading...", "Still trying...", "Help me."
    ]
}

def generate_response(incoming_text: str) -> str:
    """Generates a context-aware dumb response."""
    msg = incoming_text.lower()
    
    if any(x in msg for x in ["upi", "gpay", "paytm", "phonepe", "qr", "scan"]):
        category = "upi"
    elif any(x in msg for x in ["bank", "account", "ifsc", "statement", "branch"]):
        category = "bank"
    elif any(x in msg for x in ["link", "click", "url", "http", "website", "apk"]):
        category = "link"
    elif any(x in msg for x in ["otp", "code", "pin", "password"]):
        category = "otp"
    elif any(x in msg for x in ["police", "block", "suspend", "jail", "illegal"]):
        category = "threat"
    else:
        category = "generic"

    part1 = random.choice(ZOMBIE_MEMORY["intros"])
    part2 = random.choice(ZOMBIE_MEMORY[category])
    part3 = random.choice(ZOMBIE_MEMORY["delays"]) if random.random() > 0.5 else ""
    part4 = random.choice(ZOMBIE_MEMORY["closers"])

    return f"{part1} {part2} {part3} {part4}".replace("  ", " ").strip()

# =========================================================
# 3. INTELLIGENCE EXTRACTION (Regex)
# =========================================================
def extract_intel(history_texts: List[str]) -> dict:
    full_blob = " ".join(history_texts)
    
    return {
        "bankAccounts": list(set(re.findall(r'\b\d{9,18}\b', full_blob))),
        "upiIds": list(set(re.findall(r'[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}', full_blob))),
        "phishingLinks": list(set(re.findall(r'https?://\S+|www\.\S+', full_blob))),
        "phoneNumbers": list(set(re.findall(r'(?:\+91[\-\s]?)?[6-9]\d{9}', full_blob))),
        "suspiciousKeywords": list(set(re.findall(r'(?i)\b(block|suspend|verify|kyc|expire|urgent|police)\b', full_blob)))
    }

# =========================================================
# 4. API MODELS
# =========================================================
class MessageItem(BaseModel):
    sender: str
    text: str
    timestamp: int

class RequestPayload(BaseModel):
    sessionId: str
    message: MessageItem
    conversationHistory: List[MessageItem] = []
    metadata: Optional[Dict] = None

# =========================================================
# 5. CORE ENDPOINT
# =========================================================
@app.get("/")
def home():
    return {"status": "Zombie Honeypot Active", "platform": "Vercel"}

@app.post("/honey-pot")
async def chat_handler(payload: RequestPayload, background_tasks: BackgroundTasks):
    session_id = payload.sessionId
    user_msg = payload.message.text
    
    reply_text = generate_response(user_msg)
    
    all_msgs = [m.text for m in payload.conversationHistory]
    all_msgs.append(user_msg)
    
    intel_data = extract_intel(all_msgs)
    
    scam_keywords = ["block", "suspend", "kyc", "verify", "urgent", "expire"]
    is_scam = False
    
    if any(k in user_msg.lower() for k in scam_keywords):
        is_scam = True
    if intel_data["phishingLinks"] or intel_data["upiIds"]:
        is_scam = True

    if is_scam:
        msg_count = len(payload.conversationHistory) + 2 
        background_tasks.add_task(
            send_callback, 
            session_id, 
            is_scam, 
            msg_count, 
            intel_data
        )

    return {
        "status": "success",
        "reply": reply_text
    }

# =========================================================
# 6. CALLBACK WORKER
# =========================================================
def send_callback(session_id: str, is_scam: bool, count: int, intel: dict):
    final_payload = {
        "sessionId": session_id,
        "scamDetected": is_scam,
        "totalMessagesExchanged": count,
        "extractedIntelligence": intel,
        "agentNotes": "Zombie Agent engaged. Extracted data via regex on Vercel."
    }
    try:
        requests.post(CALLBACK_URL, json=final_payload, headers={"x-api-key": SECRET_API_KEY}, timeout=5)
        logger.info(f"Report sent for Session: {session_id}")
    except Exception as e:
        logger.error(f"Failed to send report: {e}")