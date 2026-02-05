import re
import os
import random
import logging
import unicodedata
import requests
from typing import List, Optional, Dict

from fastapi import FastAPI
from fastapi import Request
from pydantic import BaseModel

# =========================================================
# APP SETUP
# =========================================================
app = FastAPI(title="Agentic Scam HoneyPot")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HoneyPotAgent")

CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
SECRET_API_KEY = os.environ.get("team_top_250_secret")

# =========================================================
# SESSION STATE (IN-MEMORY)
# =========================================================
SESSIONS = {}

# =========================================================
# HEALTH CHECK
# =========================================================
@app.api_route("/", methods=["GET", "HEAD"])
async def health(request: Request):
    return {
        "status": "Agentic Honeypot Running",
        "endpoint": "/honey-pot",
        "platform": "Render"
    }

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
# AGENT MEMORY (ZOMBIE MODE)
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
# REQUEST MODELS
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
# CHAT ENDPOINT (NEVER STOPS EARLY)
# =========================================================
@app.post("/honey-pot")
async def honey_pot(payload: HoneyPotRequest):
    session_id = sanitize(payload.sessionId)
    incoming = sanitize(payload.message.text)

    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "messages": [],
            "intel": {
                "bankAccounts": [],
                "upiIds": [],
                "phishingLinks": [],
                "phoneNumbers": [],
                "suspiciousKeywords": []
            }
        }

    SESSIONS[session_id]["messages"].append(incoming)
    SESSIONS[session_id]["messages"] = SESSIONS[session_id]["messages"][-2000:]

    intel = extract_intelligence(SESSIONS[session_id]["messages"])

    for key in intel:
        SESSIONS[session_id]["intel"][key] = list(
            set(SESSIONS[session_id]["intel"][key] + intel[key])
        )

    reply = agent_reply(incoming)

    return {
        "status": "success",
        "reply": reply,
        "scamSignalsDetected": bool(
            SESSIONS[session_id]["intel"]["upiIds"] or
            SESSIONS[session_id]["intel"]["phishingLinks"] or
            SESSIONS[session_id]["intel"]["suspiciousKeywords"]
        )
    }

# =========================================================
# STOP ENDPOINT (GUVI CONTROLS END)
# =========================================================
@app.post("/honey-pot/stop")
async def stop_session(payload: Dict):
    session_id = sanitize(payload.get("sessionId"))

    if session_id not in SESSIONS:
        return {"status": "error", "message": "Session not found"}

    session = SESSIONS[session_id]

    final_payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": len(session["messages"]),
        "extractedIntelligence": session["intel"],
        "agentNotes": "Session stopped by GUVI after full intelligence extraction."
    }

    try:
        requests.post(
            CALLBACK_URL,
            json=final_payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": SECRET_API_KEY
            },
            timeout=5
        )
        logger.info(f"Final report sent for session {session_id}")
    except Exception as e:
        logger.error(f"Callback failed: {e}")

    del SESSIONS[session_id]

    return {
        "status": "stopped",
        "finalReport": final_payload
    }

# =========================================================
# LOCAL RUN
# =========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=1000)
