import re
import os
import random
import unicodedata
import requests
import json
from typing import List, Optional, Dict

from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel

# =========================================================
# APP SETUP
# =========================================================
app = FastAPI(title="Agentic Scam HoneyPot")

CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
SECRET_API_KEY = os.environ.get("team_top_250_secret")

# =========================================================
# JSON LOGGER (PRINT ONLY JSON)
# =========================================================
def log_json(data: dict):
    print(json.dumps(data, ensure_ascii=False))

# =========================================================
# ROOT HEALTH CHECK (FIXES 404 + 405)
# =========================================================
@app.api_route("/", methods=["GET", "HEAD"])
async def health(request: Request):
    response = {
        "status": "Agentic Honeypot Running",
        "platform": "Render",
        "endpoint": "/honey-pote"
    }
    log_json({"event": "health_check", "response": response})
    return response

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
# AGENT MEMORY
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
# RESPONSE ENGINE
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
# API ENDPOINT
# =========================================================
@app.post("/honey-pote")
async def honey_pot(payload: HoneyPotRequest, background_tasks: BackgroundTasks):
    session_id = sanitize(payload.sessionId)
    incoming = sanitize(payload.message.text)

    history = [sanitize(m.text) for m in payload.conversationHistory]
    history.append(incoming)

    if len(history) > 2000:
        history = history[-2000:]

    intel = extract_intelligence(history)

    scam_detected = bool(
        intel["upiIds"] or
        intel["phishingLinks"] or
        intel["suspiciousKeywords"]
    )

    reply = agent_reply(incoming)

    # 🔹 LOG REQUEST
    log_json({
        "event": "incoming_message",
        "sessionId": session_id,
        "message": incoming,
        "historyCount": len(history)
    })

    # 🔹 LOG ANALYSIS
    log_json({
        "event": "scam_analysis",
        "sessionId": session_id,
        "scamDetected": scam_detected,
        "intelligence": intel
    })

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
# FINAL CALLBACK
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
        log_json({
            "event": "final_callback_sent",
            "sessionId": session_id,
            "totalMessages": total_messages
        })
    except Exception as e:
        log_json({
            "event": "callback_error",
            "sessionId": session_id,
            "error": str(e)
        })

# =========================================================
# LOCAL RUN
# =========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("index:app", host="0.0.0.0", port=10000)
