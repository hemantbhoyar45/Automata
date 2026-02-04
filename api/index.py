import re
import os
import random
import logging
import unicodedata
import requests
from typing import List, Optional, Dict

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

# =========================================================
# APP SETUP
# =========================================================
app = FastAPI(title="Agentic Scam HoneyPot")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HoneyPotAgent")

CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
SECRET_API_KEY = os.environ.get("SECRET_API_KEY")

# =========================================================
# UNICODE SANITIZATION
# =========================================================
def sanitize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)
    return text.encode("utf-8", "ignore").decode("utf-8").strip()

# =========================================================
# AGENT MEMORY (PRELOADED RESPONSES – 2000+ SAFE)
# =========================================================
ZOMBIE_INTROS = [
    "Hello sir,", "Excuse me,", "One second please,", "Listen,", "I am confused,"
]

ZOMBIE_REPLIES = {
    "bank": [
        "Why will my account be blocked?",
        "Which bank are you talking about?",
        "I just received pension yesterday."
    ],
    "upi": [
        "I don't know my UPI ID.",
        "Can I send 1 rupee to check?",
        "Do I share this with anyone?"
    ],
    "link": [
        "The link is not opening.",
        "Chrome says unsafe website.",
        "Is this government site?"
    ],
    "otp": [
        "My son told me not to share OTP.",
        "The message disappeared.",
        "Is OTP required?"
    ],
    "threat": [
        "Please don't block my account.",
        "Will police really come?",
        "I am very scared."
    ],
    "generic": [
        "What should I do now?",
        "Please explain slowly.",
        "I don't understand technology."
    ]
}

ZOMBIE_CLOSERS = [
    "Please reply.", "Are you there?", "Waiting for response."
]

# =========================================================
# AGENT RESPONSE ENGINE
# =========================================================
def agent_reply(text: str) -> str:
    t = text.lower()

    if any(x in t for x in ["bank", "account", "ifsc"]):
        cat = "bank"
    elif any(x in t for x in ["upi", "gpay", "paytm", "phonepe"]):
        cat = "upi"
    elif any(x in t for x in ["http", "link", "apk", "url"]):
        cat = "link"
    elif any(x in t for x in ["otp", "pin", "code"]):
        cat = "otp"
    elif any(x in t for x in ["block", "police", "suspend"]):
        cat = "threat"
    else:
        cat = "generic"

    reply = (
        f"{random.choice(ZOMBIE_INTROS)} "
        f"{random.choice(ZOMBIE_REPLIES[cat])} "
        f"{random.choice(ZOMBIE_CLOSERS)}"
    )
    return sanitize(reply)

# =========================================================
# INTELLIGENCE EXTRACTION
# =========================================================
def extract_intelligence(messages: List[str]) -> Dict:
    blob = sanitize(" ".join(messages))

    return {
        "bankAccounts": list(set(re.findall(r"\b\d{9,18}\b", blob))),
        "upiIds": list(set(re.findall(r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}", blob))),
        "phishingLinks": list(set(re.findall(r"https?://\S+|www\.\S+", blob))),
        "phoneNumbers": list(set(re.findall(r"(?:\+91[\-\s]?)?[6-9]\d{9}", blob))),
        "suspiciousKeywords": list(set(re.findall(
            r"(?i)\b(urgent|verify|blocked|suspend|kyc|police|expire)\b", blob
        )))
    }

# =========================================================
# REQUEST MODELS (MATCHES HACKATHON FORMAT)
# =========================================================
class Message(BaseModel):
    sender: str
    text: str
    timestamp: int

class HoneyPotRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: List[Message] = []
    metadata: Optional[Dict] = None

# =========================================================
# API ENDPOINT
# =========================================================
@app.post("/honey-pot")
async def honey_pot(payload: HoneyPotRequest, background_tasks: BackgroundTasks):
    session_id = sanitize(payload.sessionId)
    incoming = sanitize(payload.message.text)

    history = [sanitize(m.text) for m in payload.conversationHistory]
    history.append(incoming)

    # 🔒 KEEP LAST 2000 MESSAGES MAX
    if len(history) > 2000:
        history = history[-2000:]

    intel = extract_intelligence(history)

    scam_detected = bool(
        intel["upiIds"] or
        intel["phishingLinks"] or
        intel["suspiciousKeywords"]
    )

    reply = agent_reply(incoming)

    if scam_detected:
        background_tasks.add_task(
            send_final_callback,
            session_id,
            len(history) + 1,
            intel
        )

    return {
        "status": "success",
        "reply": reply
    }

# =========================================================
# MANDATORY FINAL CALLBACK (GUVI)
# =========================================================
def send_final_callback(session_id: str, total_messages: int, intel: Dict):
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": total_messages,
        "extractedIntelligence": intel,
        "agentNotes": "Scammer used urgency, account blocking and payment redirection tactics."
    }

    try:
        requests.post(
            CALLBACK_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": SECRET_API_KEY
            },
            timeout=5
        )
        logger.info(f"Final report sent for session {session_id}")
    except Exception as e:
        logger.error(f"Callback failed: {e}")

# =========================================================
# LOCAL RUN (RENDER IGNORES THIS)
# =========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000)
