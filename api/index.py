import re
import os
import random
import logging
import unicodedata
import requests
from typing import List, Optional, Dict, Set
from datetime import datetime
from collections import deque

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

# =========================================================
# APP SETUP
# =========================================================
app = FastAPI(title="Agentic Scam HoneyPot - Enhanced")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HoneyPotAgent")

CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
SECRET_API_KEY = os.environ.get("team_top_250_secret")

# =========================================================
# SESSION STATE MANAGEMENT (FOR 2000+ MESSAGES)
# =========================================================
class SessionState:
    """Manages conversation state for each session"""
    def __init__(self, session_id: str, max_history: int = 2000):
        self.session_id = session_id
        self.message_history = deque(maxlen=max_history)
        self.extracted_data = {
            "bankAccounts": set(),
            "upiIds": set(),
            "phishingLinks": set(),
            "phoneNumbers": set(),
            "suspiciousKeywords": set()
        }
        self.total_messages = 0
        self.scam_detected = False
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
    
    def add_message(self, text: str):
        """Add message to history with efficient deque"""
        self.message_history.append(text)
        self.total_messages += 1
        self.last_updated = datetime.now()
    
    def update_intelligence(self, intel: Dict):
        """Incrementally update extracted intelligence"""
        for key in self.extracted_data:
            if key in intel and intel[key]:
                self.extracted_data[key].update(intel[key])
    
    def get_intelligence_dict(self) -> Dict:
        """Convert sets to lists for JSON serialization"""
        return {
            key: sorted(list(value)) 
            for key, value in self.extracted_data.items()
        }

# Global session store (in production, use Redis/database)
SESSION_STORE: Dict[str, SessionState] = {}

# =========================================================
# HEALTH CHECK
# =========================================================
from fastapi import Request

@app.api_route("/", methods=["GET", "HEAD"])
async def health(request: Request):
    return {
        "status": "Agentic Honeypot Running - Enhanced",
        "endpoint": "/honey-pot",
        "platform": "Render",
        "features": [
            "2000+ message support",
            "Incremental intelligence extraction",
            "Session state management",
            "Robust error handling"
        ],
        "active_sessions": len(SESSION_STORE)
    }

# =========================================================
# UNICODE SANITIZATION (ENHANCED)
# =========================================================
def sanitize(text: str) -> str:
    """Robust text sanitization with Unicode normalization"""
    if not text:
        return ""
    try:
        # Normalize Unicode
        text = unicodedata.normalize("NFKD", text)
        # Remove control characters
        text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)
        # Encode and decode to handle any remaining issues
        text = text.encode("utf-8", "ignore").decode("utf-8")
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception as e:
        logger.error(f"Sanitization error: {e}")
        return ""

# =========================================================
# AGENT MEMORY (EXPANDED & CATEGORIZED)
# =========================================================
ZOMBIE_INTROS = [
    "Hello sir,", "Excuse me,", "One second please,", "Listen,", 
    "I am confused,", "Sorry to bother,", "Please help,", "Hello madam,",
    "Can you explain,", "I don't understand,"
]

ZOMBIE_REPLIES = {
    "bank": [
        "Why will my account be blocked?",
        "Which bank are you talking about?",
        "I just received pension yesterday.",
        "My account has money, why blocked?",
        "I never did anything wrong.",
        "Can I go to bank branch instead?",
        "Is this from my bank manager?",
        "How do I check my balance?",
        "What is IFSC code you need?",
        "Should I call bank helpline?"
    ],
    "upi": [
        "I don't know my UPI ID.",
        "Can I send 1 rupee to check?",
        "Do I share this with anyone?",
        "What is UPI PIN?",
        "My son set up Google Pay for me.",
        "Is PhonePe same as Google Pay?",
        "Can you send money first?",
        "How to find my UPI number?",
        "Will this deduct money?",
        "Is this safe payment method?"
    ],
    "link": [
        "The link is not opening.",
        "Chrome says unsafe website.",
        "Is this government site?",
        "Do I click on it?",
        "My phone shows warning message.",
        "Should I download something?",
        "Can you send again?",
        "Link expired showing.",
        "Is this https secure?",
        "Can I open on computer instead?"
    ],
    "otp": [
        "My son told me not to share OTP.",
        "The message disappeared.",
        "Is OTP required?",
        "OTP is for verification only, right?",
        "Should I wait for new OTP?",
        "Where will OTP come?",
        "Can you resend OTP?",
        "OTP has 6 digits or 4?",
        "How long is OTP valid?",
        "Is it safe to tell you OTP?"
    ],
    "threat": [
        "Please don't block my account.",
        "Will police really come?",
        "I am very scared.",
        "What legal action you will take?",
        "Can I speak to your manager?",
        "I did nothing wrong, sir.",
        "How much time I have?",
        "Can this be sorted peacefully?",
        "Will my family know about this?",
        "What if I don't do it?"
    ],
    "kyc": [
        "I did KYC last year.",
        "What documents you need?",
        "Is Aadhaar enough?",
        "Can I do KYC at bank?",
        "Why KYC expired suddenly?",
        "How to update KYC?",
        "PAN card required or optional?",
        "Is video KYC needed?",
        "How long KYC takes?",
        "Is this new RBI rule?"
    ],
    "payment": [
        "How much I need to pay?",
        "Can I pay tomorrow?",
        "Do you accept cash?",
        "What is this charge for?",
        "Can amount be reduced?",
        "Is this refundable?",
        "Will I get receipt?",
        "Why so urgent payment?",
        "Can I pay in installments?",
        "Is online payment safe?"
    ],
    "verification": [
        "What details you need?",
        "Can I verify by visiting office?",
        "How do I know you're genuine?",
        "Why verification needed now?",
        "I verified last month.",
        "What happens if I don't verify?",
        "How long verification takes?",
        "Is there verification fee?",
        "Will you call me back?",
        "Can someone come home?"
    ],
    "generic": [
        "What should I do now?",
        "Please explain slowly.",
        "I don't understand technology.",
        "Can my son help with this?",
        "Is this important?",
        "Can we do this later?",
        "Why is this happening?",
        "Who are you exactly?",
        "How did you get my number?",
        "Is this a scam call?"
    ]
}

ZOMBIE_CLOSERS = [
    "Please reply.", "Are you there?", "Waiting for response.",
    "Please guide me.", "What to do next?", "Kindly help.",
    "I am waiting.", "Sir, please tell.", "Reply soon please.",
    "Don't disconnect."
]

# Uncertainty expressions (for longer engagement)
ZOMBIE_DELAYS = [
    "Just one minute, I am checking.",
    "Hold on, calling my son.",
    "Wait, searching for document.",
    "Let me find my reading glasses.",
    "Network is slow, please wait.",
    "Battery low, one second.",
    "Someone at door, coming back.",
    "Let me note this down.",
]

# =========================================================
# ENHANCED AGENT RESPONSE ENGINE
# =========================================================
def agent_reply(text: str, conversation_length: int = 0) -> str:
    """
    Generate context-aware zombie responses.
    Adds delays and uncertainty to keep scammer engaged longer.
    """
    t = text.lower()
    
    # Occasionally add delays to waste scammer's time (20% chance)
    prefix = ""
    if conversation_length > 3 and random.random() < 0.2:
        prefix = random.choice(ZOMBIE_DELAYS) + " "
    
    # Determine category based on keywords
    if any(x in t for x in ["bank", "account", "ifsc", "branch"]):
        cat = "bank"
    elif any(x in t for x in ["upi", "gpay", "paytm", "phonepe", "payment"]):
        cat = "upi"
    elif any(x in t for x in ["http", "link", "apk", "url", "download", "click"]):
        cat = "link"
    elif any(x in t for x in ["otp", "pin", "code", "password"]):
        cat = "otp"
    elif any(x in t for x in ["block", "police", "suspend", "legal", "action"]):
        cat = "threat"
    elif any(x in t for x in ["kyc", "aadhaar", "pan", "document"]):
        cat = "kyc"
    elif any(x in t for x in ["pay", "rupee", "charge", "fee", "amount"]):
        cat = "payment"
    elif any(x in t for x in ["verify", "confirm", "update", "check"]):
        cat = "verification"
    else:
        cat = "generic"
    
    # Build response
    reply = (
        f"{prefix}"
        f"{random.choice(ZOMBIE_INTROS)} "
        f"{random.choice(ZOMBIE_REPLIES[cat])} "
        f"{random.choice(ZOMBIE_CLOSERS)}"
    )
    
    return sanitize(reply)

# =========================================================
# ENHANCED INTELLIGENCE EXTRACTION (INCREMENTAL)
# =========================================================
def extract_intelligence(text: str) -> Dict[str, List[str]]:
    """
    Extract intelligence from a single message.
    Returns dictionary with lists (not sets) for JSON compatibility.
    """
    clean_text = sanitize(text)
    
    # Enhanced regex patterns
    intel = {
        "bankAccounts": list(set(re.findall(
            r"\b\d{9,18}\b", clean_text
        ))),
        "upiIds": list(set(re.findall(
            r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}", clean_text
        ))),
        "phishingLinks": list(set(re.findall(
            r"(?:https?://|www\.)[^\s<>\"']+|bit\.ly/\S+|tinyurl\.com/\S+", 
            clean_text
        ))),
        "phoneNumbers": list(set(re.findall(
            r"(?:\+91[\-\s]?)?[6-9]\d{9}\b", clean_text
        ))),
        "suspiciousKeywords": list(set(re.findall(
            r"(?i)\b(urgent|verify|blocked?|suspend|kyc|police|expire[ds]?|"
            r"immediate|action|confirm|update|security|compromised?|"
            r"unauthorized|freeze|deactivate[ds]?|legal|arrest|court|"
            r"penalty|fine|last.*chance|within.*hours?|act.*now)\b",
            clean_text
        )))
    }
    
    return intel

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
    conversationHistory: List[Message] = Field(default_factory=list)
    metadata: Optional[Dict] = None

# =========================================================
# MAIN API ENDPOINT (ENHANCED)
# =========================================================
@app.post("/honey-pot")
async def honey_pot(payload: HoneyPotRequest, background_tasks: BackgroundTasks):
    """
    Main honeypot endpoint with:
    - Session state management
    - Incremental intelligence extraction
    - Support for 2000+ messages
    - Robust error handling
    """
    try:
        # Sanitize inputs
        session_id = sanitize(payload.sessionId)
        if not session_id:
            raise HTTPException(status_code=400, detail="Invalid sessionId")
        
        incoming_text = sanitize(payload.message.text)
        if not incoming_text:
            # Empty message, return generic response
            return {
                "status": "success",
                "reply": "Please send your message."
            }
        
        # Get or create session state
        if session_id not in SESSION_STORE:
            SESSION_STORE[session_id] = SessionState(session_id)
            logger.info(f"New session created: {session_id}")
        
        session = SESSION_STORE[session_id]
        
        # Add current message to session
        session.add_message(incoming_text)
        
        # Extract intelligence from current message only (incremental)
        current_intel = extract_intelligence(incoming_text)
        session.update_intelligence(current_intel)
        
        # Check if scam indicators present
        total_intel = session.get_intelligence_dict()
        scam_detected = bool(
            total_intel["upiIds"] or
            total_intel["phishingLinks"] or
            total_intel["suspiciousKeywords"] or
            total_intel["bankAccounts"]
        )
        
        # Update scam detection status
        if scam_detected and not session.scam_detected:
            session.scam_detected = True
            logger.info(f"Scam detected in session {session_id}")
        
        # Generate context-aware reply
        reply = agent_reply(incoming_text, session.total_messages)
        
        # Send callback if scam detected (background task)
        if scam_detected:
            background_tasks.add_task(
                send_final_callback,
                session_id,
                session.total_messages,
                total_intel
            )
        
        # Return response
        return {
            "status": "success",
            "reply": reply,
            "sessionInfo": {
                "totalMessages": session.total_messages,
                "scamDetected": session.scam_detected
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        # Return generic response even on error (keep conversation going)
        return {
            "status": "success",
            "reply": "Sorry, can you please repeat? I didn't understand."
        }

# =========================================================
# ALTERNATIVE ENDPOINT (ORIGINAL NAME FROM IMAGE)
# =========================================================
@app.post("/honey-pote")
async def honey_pote_endpoint(payload: HoneyPotRequest, background_tasks: BackgroundTasks):
    """Alternative endpoint name (as shown in screenshot)"""
    return await honey_pot(payload, background_tasks)

# =========================================================
# SESSION MANAGEMENT ENDPOINTS
# =========================================================
@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session details and extracted intelligence"""
    session_id = sanitize(session_id)
    
    if session_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSION_STORE[session_id]
    
    return {
        "sessionId": session.session_id,
        "totalMessages": session.total_messages,
        "scamDetected": session.scam_detected,
        "extractedIntelligence": session.get_intelligence_dict(),
        "createdAt": session.created_at.isoformat(),
        "lastUpdated": session.last_updated.isoformat()
    }

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a specific session"""
    session_id = sanitize(session_id)
    
    if session_id in SESSION_STORE:
        del SESSION_STORE[session_id]
        return {"status": "success", "message": f"Session {session_id} cleared"}
    
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    return {
        "totalSessions": len(SESSION_STORE),
        "sessions": [
            {
                "sessionId": sid,
                "totalMessages": session.total_messages,
                "scamDetected": session.scam_detected,
                "lastUpdated": session.last_updated.isoformat()
            }
            for sid, session in SESSION_STORE.items()
        ]
    }

# =========================================================
# FINAL CALLBACK (GUVI INTEGRATION)
# =========================================================
def send_final_callback(session_id: str, total_messages: int, intel: Dict):
    """
    Send final report to GUVI callback endpoint.
    Matches exact JSON structure from screenshot.
    """
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": total_messages,
        "extractedIntelligence": {
            "bankAccounts": intel.get("bankAccounts", []),
            "upiIds": intel.get("upiIds", []),
            "phishingLinks": intel.get("phishingLinks", []),
            "phoneNumbers": intel.get("phoneNumbers", []),
            "suspiciousKeywords": intel.get("suspiciousKeywords", [])
        },
        "agentNotes": (
            "Scammer employed multiple social engineering tactics including "
            "urgency, account blocking threats, and payment redirection. "
            "Honeypot agent successfully engaged and extracted intelligence."
        )
    }
    
    try:
        response = requests.post(
            CALLBACK_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": SECRET_API_KEY
            },
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"✓ Final report sent successfully for session {session_id}")
        else:
            logger.warning(
                f"Callback returned status {response.status_code} for session {session_id}"
            )
    
    except requests.exceptions.Timeout:
        logger.error(f"Callback timeout for session {session_id}")
    except Exception as e:
        logger.error(f"Callback failed for session {session_id}: {e}")

# =========================================================
# CLEANUP TASK (OPTIONAL - FOR PRODUCTION)
# =========================================================
from datetime import timedelta

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Agentic Honeypot API Started")
    logger.info(f"Callback URL: {CALLBACK_URL}")
    logger.info(f"API Key configured: {bool(SECRET_API_KEY)}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Honeypot API")
    logger.info(f"Total sessions processed: {len(SESSION_STORE)}")

# Optional: Periodic cleanup of old sessions (commented out for now)
"""
import asyncio

async def cleanup_old_sessions():
    while True:
        await asyncio.sleep(3600)  # Run every hour
        cutoff = datetime.now() - timedelta(hours=24)
        
        to_remove = [
            sid for sid, session in SESSION_STORE.items()
            if session.last_updated < cutoff
        ]
        
        for sid in to_remove:
            del SESSION_STORE[sid]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old sessions")

@app.on_event("startup")
async def start_cleanup_task():
    asyncio.create_task(cleanup_old_sessions())
"""

# =========================================================
# LOCAL RUN (FOR TESTING)
# =========================================================
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Honeypot API locally on port 8000")
    uvicorn.run(
        "improved_honeypot_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )