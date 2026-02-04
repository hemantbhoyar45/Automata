import re
import logging
import random
import requests
import os
import unicodedata
from typing import List, Optional, Dict

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

# =========================================================
# 1. SETUP & CONFIGURATION
# =========================================================
app = FastAPI(title="GUVI Zombie HoneyPot")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ZombieAgent")

CALLBACK_URL = os.environ.get(
    "CALLBACK_URL",
    "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
)
SECRET_API_KEY = os.environ.get("SECRET_API_KEY", "YOUR_SECRET_API_KEY_HERE")

# =========================================================
# 2. UNICODE SANITIZER (STEP 1–2)
# =========================================================
def sanitize_text(text: str) -> str:
    """
    Normalizes unicode, removes control characters,
    and ensures UTF-8 safe JSON strings.
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    text = text.encode("utf-8", "ignore").decode("utf-8")

    return text.strip()

# =========================================================
# 3. ZOMBIE RESPONSE MEMORY
# =========================================================
ZOMBIE_MEMORY = {
    "intros": [
        "Hello sir,", "Excuse me,", "Oh my god,", "Wait,", "Listen,",
        "Actually,", "One second,", "Sir/Madam,", "I am confused,",
        "Sorry for delay,", "Please help me,"
    ],
    "upi": [
        "my GPay is showing server error.",
        "PhonePe is asking for my PIN.",
        "the QR code is not scanning.",
        "my bank server is down I think."
    ],
    "bank": [
        "I cannot find my passbook.",
        "the IFSC code shows invalid.",
        "my ATM card is broken."
    ],
    "link": [
        "the link is not opening.",
        "chrome says malware detected.",
        "it asks me to download APK."
    ],
    "otp": [
        "I did not receive any OTP.",
        "message came but vanished.",
        "my son told me not to share code."
    ],
    "threat": [
        "please do not block my account.",
        "will police come to my house?",
        "I am very scared."
    ],
    "generic": [
        "I don't understand this.",
        "what should I do next?",
        "is this real or fake?"
    ],
    "delays": [
        "Just one minute please.",
        "Restarting my phone.",
        "Network is very slow."
    ],
    "closers": [
        "Are you there?",
        "Please reply.",
        "Waiting for you."
    ]
}

# =========================================================
# 4. RESPONSE GENERATOR (STEP 4)
# =========================================================
def generate_response(incoming_text: str) -> str:
    msg = incoming_text.lower()

    if any(x in msg for x in ["upi", "gpay", "paytm", "phonepe", "qr"]):
        category = "upi"
    elif any(x in msg for x in ["bank", "account", "ifsc"]):
        category = "bank"
    elif any(x in msg for x in ["link", "url", "http", "apk"]):
        category = "link"
    elif any(x in msg for x in ["otp", "pin", "code"]):
        category = "otp"
    elif any(x in msg for x in ["block", "police", "illegal"]):
        category = "threat"
    else:
        category = "generic"

    response = f"{random.choice(ZOMBIE_MEMORY['intros'])} " \
               f"{random.choice(ZOMBIE_MEMORY[category])} " \
               f"{random.choice(ZOMBIE_MEMORY['delays']) if random.random() > 0.5 else ''} " \
               f"{random.choice(ZOMBIE_MEMORY['closers'])}"

    return sanitize_text(response.replace("  ", " ").strip())

# =========================================================
# 5. INTELLIGENCE EXTRACTION (STEP 3)
# =========================================================
def extract_intel(history: List[str]) -> dict:
    safe_blob = sanitize_text(" ".join(history))

    return {
        "bankAccounts": list(set(re.findall(r"\b\d{9,18}\b", safe_blob))),
        "upiIds": list(set(re.findall(r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}", safe_blob))),
        "phishingLinks": list(set(re.findall(r"https?://\S+|www\.\S+", safe_blob))),
        "phoneNumbers": list(set(re.findall(r"(?:\+91[\-\s]?)?[6-9]\d{9}", safe_blob))),
        "suspiciousKeywords": list(set(re.findall(
            r"(?i)\b(block|suspend|verify|kyc|urgent|expire|police)\b", safe_blob
        )))
    }

# =========================================================
# 6. API MODELS
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
# 7. ROUTES
# =========================================================
@app.get("/")
def home():
    return {"status": "Zombie Honeypot Active"}

@app.post("/honey-pot")
async def chat_handler(payload: RequestPayload, background_tasks: BackgroundTasks):
    session_id = sanitize_text(payload.sessionId)
    user_msg = sanitize_text(payload.message.text)

    logger.info(f"Incoming message: {repr(user_msg)}")

    reply = generate_response(user_msg)

    history = [sanitize_text(m.text) for m in payload.conversationHistory]
    history.append(user_msg)

    intel = extract_intel(history)

    is_scam = bool(
        intel["upiIds"] or
        intel["phishingLinks"] or
        intel["suspiciousKeywords"]
    )

    if is_scam:
        background_tasks.add_task(
            send_callback,
            session_id,
            True,
            len(history) + 1,
            intel
        )

    return {
        "status": "success",
        "reply": reply
    }

# =========================================================
# 8. CALLBACK SENDER (STEP 5)
# =========================================================
def send_callback(session_id: str, is_scam: bool, count: int, intel: dict):
    payload = {
        "sessionId": sanitize_text(session_id),
        "scamDetected": is_scam,
        "totalMessagesExchanged": count,
        "extractedIntelligence": intel,
        "agentNotes": sanitize_text(
            "Zombie Agent engaged. Unicode sanitized. JSON safe."
        )
    }

    try:
        requests.post(
            CALLBACK_URL,
            json=payload,
            headers={"x-api-key": SECRET_API_KEY},
            timeout=5
        )
        logger.info(f"Callback sent for session {session_id}")
    except Exception as e:
        logger.error(f"Callback failed: {e}")
