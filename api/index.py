import re
import os
import random
import logging
import unicodedata
import requests
import json
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel

# =========================================================
# APP SETUP
# =========================================================
app = FastAPI(title="Agentic Scam HoneyPot")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HoneyPotAgent")

CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
SECRET_API_KEY = os.environ.get("team_top_250_secret")
DATA_FILE = "honeypot_sessions.json"

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
# AGENT MEMORY (ZOMBIE PERSONA - Rule 4)
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
    elif any(x in t for x in ["block", "police", "suspend", "urgent", "verify"]):
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
# INTELLIGENCE EXTRACTION (Rule 3)
# =========================================================
def extract_intelligence(messages: List[str]) -> Dict:
    blob = sanitize(" ".join(messages))
    
    return {
        "bankAccounts": list(set(re.findall(r"\b\d{9,18}\b", blob))),
        "upiIds": list(set(re.findall(r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}", blob))),
        "phishingLinks": list(set(re.findall(r"https?://\S+|www\.\S+", blob))),
        "phoneNumbers": list(set(re.findall(r"(?:\+91[\-\s]?)?[6-9]\d{9}", blob))),
        # Updated Regex to match Rule 3 Keywords strictly
        "suspiciousKeywords": list(set(re.findall(
            r"(?i)\b(urgent|blocked|suspend|kyc|police|verify)\b", blob
        )))
    }

# =========================================================
# HELPER: SAVE JSON & SEND CALLBACK
# =========================================================
def save_session_to_json(session_id: str, messages: list, intel: dict):
    record = {
        "sessionId": session_id,
        "endedAt": datetime.utcnow().isoformat(),
        "conversation": messages,
        "extractedIntelligence": intel
    }
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        data.append(record)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Session {session_id} saved to JSON")
    except Exception as e:
        logger.error(f"Failed to save JSON file: {e}")

def send_final_callback(session_id: str, total_messages: int, intel: Dict):
    # Rule 5: Generate Final Output strictly in JSON
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": total_messages,
        "extractedIntelligence": intel,
        "agentNotes": "Scam indicator detected. Session terminated as per Rule 5."
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
# CORE ENDPOINT (Strict Rule Compliance)
# =========================================================
@app.post("/honey-pot")
async def honey_pot(payload: HoneyPotRequest, background_tasks: BackgroundTasks):
    session_id = sanitize(payload.sessionId)
    incoming = sanitize(payload.message.text)
    
    # 1. Initialize Session
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "messages": [], 
            "intel": {
                "bankAccounts": [], "upiIds": [], "phishingLinks": [], 
                "phoneNumbers": [], "suspiciousKeywords": []
            }
        }
    
    # 2. Store Message
    SESSIONS[session_id]["messages"].append(incoming)
    # Keep strictly last 2000 messages
    SESSIONS[session_id]["messages"] = SESSIONS[session_id]["messages"][-2000:]
    
    # 3. Continuous Extraction
    intel = extract_intelligence(SESSIONS[session_id]["messages"])
    
    # Update Session Intel
    for key in intel:
        SESSIONS[session_id]["intel"][key] = list(
            set(SESSIONS[session_id]["intel"][key] + intel[key])
        )

    # 4. SCAM DETECTION LOGIC (Rule 3 & 5)
    # Check if ANY indicator is found (including keywords like 'urgent')
    scam_detected = bool(
        SESSIONS[session_id]["intel"]["upiIds"] or 
        SESSIONS[session_id]["intel"]["phishingLinks"] or 
        SESSIONS[session_id]["intel"]["suspiciousKeywords"] or
        SESSIONS[session_id]["intel"]["bankAccounts"] or
        SESSIONS[session_id]["intel"]["phoneNumbers"]
    )
    
    reply = agent_reply(incoming)
    
    # Rule 5: If detected -> Stop extending -> Send Final JSON -> End Session
    if scam_detected:
        # Send Callback immediately (Satisfies "Generate final output")
        background_tasks.add_task(
            send_final_callback, 
            session_id, 
            len(SESSIONS[session_id]["messages"]), 
            SESSIONS[session_id]["intel"]
        )
        # Save to Local JSON File
        background_tasks.add_task(
            save_session_to_json, 
            session_id, 
            SESSIONS[session_id]["messages"], 
            SESSIONS[session_id]["intel"]
        )
        # We assume session ends here for the evaluator logic
        # But we still return the final reply to the scammer
        
        # Optional: Clear memory to "End the session" internally
        # del SESSIONS[session_id] 
        # (Commented out to allow /stop endpoint to still find it if needed)

    # Rule 7: If no indicators, continue indefinitely (we just return reply)
    return {
        "status": "success",
        "reply": reply,
        "scamDetected": scam_detected
    }

# =========================================================
# STOP ENDPOINT (Manual Override - Rule 1 & 5 Support)
# =========================================================
@app.post("/honey-pot/stop")
async def stop_session(payload: Dict):
    session_id = sanitize(payload.get("sessionId"))
    if session_id not in SESSIONS:
        return {"status": "error", "message": "Session not found"}
    
    session = SESSIONS[session_id]
    
    # Trigger final callback manually if not already triggered
    background_tasks = BackgroundTasks()
    background_tasks.add_task(
        send_final_callback, 
        session_id, 
        len(session["messages"]), 
        session["intel"]
    )
    background_tasks.add_task(
        save_session_to_json, 
        session_id, 
        session["messages"], 
        session["intel"]
    )
    
    del SESSIONS[session_id]
    return {
        "status": "stopped", 
        "message": "Session finalized manually"
    }

# =========================================================
# LOCAL RUN
# =========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=1000)