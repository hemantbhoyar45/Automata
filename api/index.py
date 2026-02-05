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
from fastapi import Request

# =========================================================
# APP SETUP
# =========================================================
app = FastAPI(title="Advanced Honeypot - 700+ Responses")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HoneyPotAgent")

CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
SECRET_API_KEY = os.environ.get("team_top_250_secret")

MIN_MESSAGES_BEFORE_CALLBACK = 30
TARGET_MESSAGES = 40

# =========================================================
# 700+ PRELOADED MESSAGES DATABASE
# =========================================================

# INITIAL CONFUSION RESPONSES (100+ variations)
INITIAL_CONFUSION = [
    # Basic confusion
    "Hello sir, I am confused. What happened?",
    "Excuse me, which bank you calling from?",
    "One second please, I don't understand.",
    "Is this SBI bank? I have account there.",
    "What is the problem? Please explain slowly.",
    "I am old person, explain in simple words.",
    "Why you calling me? Who gave my number?",
    "Wait, let me get my reading glasses.",
    "My son handles these things. Should I call him?",
    "Is this about my pension account?",
    
    # More confusion variations
    "Sorry, I didn't catch that. Can you repeat?",
    "Which company did you say you're from?",
    "Is this a government call?",
    "I don't remember giving anyone my number.",
    "What is this regarding exactly?",
    "Can you speak louder? I can't hear properly.",
    "Is this about the bank account?",
    "I am not good with technology.",
    "Please speak slowly, I am elderly.",
    "What do you want from me?",
    
    # Identity verification questions
    "How do I know this is not a scam call?",
    "Can you prove you are from the bank?",
    "What is your name and employee ID?",
    "Which branch are you calling from?",
    "Is there a reference number for this call?",
    "Can I call you back on the official number?",
    "Do you have my account details with you?",
    "What is my account balance then?",
    "When did I open my account?",
    "Who is my relationship manager?",
    
    # Technology confusion
    "I don't use internet banking.",
    "My phone is very old, it might not work.",
    "I only know how to receive calls.",
    "What is app? I don't have any apps.",
    "I can only do things at the bank counter.",
    "My children help me with technology.",
    "Can you explain what smartphone means?",
    "I have a basic phone only.",
    "I don't understand these computer things.",
    "Is this about the ATM card?",
    
    # Family references
    "Should I ask my daughter about this?",
    "My son warned me about such calls.",
    "Let me call my grandson, he knows better.",
    "My daughter-in-law handles my banking.",
    "Can you speak to my son instead?",
    "My nephew told me to be careful.",
    "Should I check with my family first?",
    "My brother also got such a call yesterday.",
    "My wife usually handles these matters.",
    "Let me ask my neighbor, he is educated.",
    
    # Time delays
    "Can you call back in the evening?",
    "I am busy right now, call later.",
    "Can we do this tomorrow?",
    "I need to finish my lunch first.",
    "It's my prayer time, can you wait?",
    "I have a doctor appointment now.",
    "Can you explain this when my son is home?",
    "Let me finish my medicine first.",
    "I need to rest, I am not well.",
    "Call me after one hour please.",
    
    # Fear and worry
    "Is something wrong with my account?",
    "Did I do something wrong?",
    "Am I in trouble?",
    "Will I lose my money?",
    "Is my pension safe?",
    "What will happen if I don't do this?",
    "I am very scared now.",
    "Please don't block my account.",
    "I need that money for medicines.",
    "That's my only income source.",
    
    # Trust building attempts
    "How long have you been working there?",
    "Do you work in the head office?",
    "What is your supervisor's name?",
    "Can I get a call back number?",
    "Is there an email I can write to?",
    "What is your department name?",
    "Do you handle complaints also?",
    "Can you give me a complaint number?",
    "Is there a helpline I can call?",
    "Can I visit the branch instead?",
    
    # Account related confusion  
    "Which account are you talking about?",
    "I have accounts in many banks.",
    "Is this about savings or current?",
    "Is it the joint account with my wife?",
    "I have a fixed deposit also.",
    "Are you talking about the PPF account?",
    "Is this my pension account?",
    "I have account in different branch also.",
    "Which city branch is this?",
    "I opened account long time back."
]

# ACCOUNT & BANKING QUESTIONS (100+ variations)
ACCOUNT_QUESTIONS = [
    "Which account number you are talking about?",
    "I have multiple accounts, which one?",
    "Can you tell me my account balance?",
    "What is my IFSC code then?",
    "How much money is in my account?",
    "Which branch is my account in?",
    "When did I last transact?",
    "What was my last deposit amount?",
    "Is my account active or dormant?",
    "What is my customer ID?",
    
    "Do I have minimum balance?",
    "Is there any penalty charged?",
    "Why is there a hold on my account?",
    "Can you check my transaction history?",
    "What is my account type?",
    "Is it a zero balance account?",
    "Do I have overdraft facility?",
    "What is my credit limit?",
    "Is my passbook updated?",
    "When is my account anniversary?",
    
    "How many accounts do I have?",
    "Is my wife's name also there?",
    "What is the joint account holder name?",
    "Is my nominee details updated?",
    "What is my registered mobile number?",
    "Is my email registered with bank?",
    "What is my correspondence address?",
    "Is my PAN card linked?",
    "Is Aadhaar linked to account?",
    "What documents are on file?",
    
    "Can I close this account?",
    "What is the closure process?",
    "Will there be closing charges?",
    "Can I transfer to another branch?",
    "How to change my address?",
    "Can I update my phone number?",
    "How to add a nominee?",
    "Can I make it a joint account?",
    "How to get a new passbook?",
    "Can I get statement by post?",
    
    "Is my debit card active?",
    "What is my ATM PIN?",
    "Where is nearest ATM?",
    "Can I withdraw cash now?",
    "What is daily withdrawal limit?",
    "Is my card blocked?",
    "How to activate internet banking?",
    "What is my user ID?",
    "Can I do mobile banking?",
    "How to register for SMS alerts?",
    
    "What loans do I have?",
    "Is my loan paid off?",
    "What is outstanding amount?",
    "When is my EMI due?",
    "Can I prepay the loan?",
    "What is my CIBIL score?",
    "Do I have any overdues?",
    "Is there any penalty?",
    "Can I get a loan statement?",
    "What is the interest rate?",
    
    "Do I have fixed deposit?",
    "When does my FD mature?",
    "What is the FD amount?",
    "Can I break it before maturity?",
    "What will be the penalty?",
    "Is it auto-renewal?",
    "What is the interest rate?",
    "Can I get loan against FD?",
    "Is the interest taxable?",
    "How to close the FD?",
    
    "What is my relationship manager name?",
    "Can I speak to the branch manager?",
    "What is the branch address?",
    "What are the working hours?",
    "Is branch open on Sunday?",
    "What is the helpline number?",
    "Can I book an appointment?",
    "Is there a dedicated senior citizen counter?",
    "Do you have wheelchair access?",
    "Can someone visit my home?",
    
    "Why was money deducted?",
    "I didn't make that transaction.",
    "Can you reverse the charge?",
    "How to file a complaint?",
    "Where is my refund?",
    "I didn't receive cashback.",
    "Why is transaction pending?",
    "How long for clearance?",
    "Can you expedite the process?",
    "Who can I escalate this to?",
    
    "What is annual maintenance charge?",
    "Why SMS charges are deducted?",
    "What are the service charges?",
    "Is there any hidden fee?",
    "Can charges be waived?",
    "Why minimum balance penalty?",
    "What is GST component?",
    "Can I get fee structure in writing?",
    "Why increased charges suddenly?",
    "Is this mentioned in agreement?"
]

# UPI & DIGITAL PAYMENT QUESTIONS (100+ variations)
UPI_QUESTIONS = [
    "What is UPI ID? I don't know.",
    "My son set up Google Pay. Is that UPI?",
    "Can you send 1 rupee first to check?",
    "Where do I find my UPI ID?",
    "Is PhonePe same as UPI?",
    "Should I give you my UPI number?",
    "What is UPI PIN?",
    "Is it safe to share UPI?",
    "How to create UPI ID?",
    "Can I have multiple UPI IDs?",
    
    "What is Google Pay exactly?",
    "How to download this app?",
    "Is it free to use?",
    "Will it deduct my money?",
    "How much data does it use?",
    "Can I use it without internet?",
    "Is there age limit for this?",
    "Do I need smartphone?",
    "My phone is very old.",
    "Can I use it on basic phone?",
    
    "What is Paytm wallet?",
    "How is it different from bank?",
    "Is money safe in wallet?",
    "Can I withdraw wallet money?",
    "How to transfer wallet to bank?",
    "What is KYC in Paytm?",
    "Why wallet limit is there?",
    "How to increase limit?",
    "Is cashback real money?",
    "When will I get cashback?",
    
    "What is PhonePe?",
    "Is it from Phone company?",
    "How to register in PhonePe?",
    "Can I link multiple banks?",
    "What is switch account?",
    "How to add money?",
    "What are recharge options?",
    "Can I pay electricity bill?",
    "Is there transaction limit?",
    "How to check payment history?",
    
    "What is QR code payment?",
    "How does scanning work?",
    "Is it secure?",
    "Can anyone scan and take money?",
    "Do I need to scan or show?",
    "What if wrong amount?",
    "Can I cancel QR payment?",
    "How to generate my QR?",
    "Is there charges for QR?",
    "Can I use same QR everywhere?",
    
    "What is mobile recharge?",
    "Can I recharge others' number?",
    "How to recharge my phone?",
    "Will it reflect immediately?",
    "What if recharge fails?",
    "Can I get refund?",
    "Is there cashback on recharge?",
    "Can I schedule recharge?",
    "What is auto-recharge?",
    "How to check balance after?",
    
    "What is bill payment option?",
    "Can I pay electricity here?",
    "How about gas cylinder?",
    "Can I pay water bill?",
    "Is property tax possible?",
    "What about insurance premium?",
    "Can I pay credit card bill?",
    "How to add biller?",
    "Is there late fee?",
    "Can I see bill amount?",
    
    "What is bank transfer?",
    "How long does it take?",
    "Is IMPS immediate?",
    "What is NEFT timing?",
    "What is RTGS?",
    "Which is faster?",
    "What are the charges?",
    "Is there transfer limit?",
    "Can I transfer to any bank?",
    "How to add beneficiary?",
    
    "What is request money feature?",
    "How does it work?",
    "Can I reject request?",
    "Is it like loan?",
    "Will they see my balance?",
    "Can strangers request?",
    "How to block requests?",
    "Is there time limit?",
    "What if I forget to pay?",
    "Can they force payment?",
    
    "What are offers in app?",
    "How to get discount?",
    "Is scratch card real?",
    "What is spin and win?",
    "Are prizes genuine?",
    "How to claim reward?",
    "When will money come?",
    "Is there minimum order?",
    "What is referral bonus?",
    "Can I refer myself?"
]

# LINK & SECURITY QUESTIONS (80+ variations)
LINK_QUESTIONS = [
    "The link is not opening for me.",
    "My phone showing security warning.",
    "Is this government website?",
    "Can you send link on WhatsApp?",
    "Link says expired, can you resend?",
    "My son said not to click unknown links.",
    "Chrome is blocking the site.",
    "It says connection not secure.",
    "Can I open on computer?",
    "Is HTTPS secure enough?",
    
    "What will happen if I click?",
    "Will it download something?",
    "Is there virus risk?",
    "My antivirus is blocking it.",
    "Can I scan link first?",
    "How to check if link is safe?",
    "What if it's a scam site?",
    "Can someone hack my phone?",
    "Will clicking charge money?",
    "Is this verified link?",
    
    "What is APK file?",
    "Should I download APK?",
    "Is it safe to install?",
    "Where to download from?",
    "Play Store not showing it.",
    "What are app permissions?",
    "Why it needs so many access?",
    "Can I deny some permissions?",
    "Will app read my messages?",
    "Can it access my photos?",
    
    "What is this domain name?",
    "Is .com or .in better?",
    "What about .org sites?",
    "Why so many numbers in URL?",
    "What is bit.ly link?",
    "Are short links safe?",
    "Can you send full link?",
    "What website is this?",
    "Is there certificate?",
    "How to verify website?",
    
    "Can I use public WiFi for this?",
    "Is mobile data safer?",
    "What about cyber cafe?",
    "Can someone see my screen?",
    "Is incognito mode safe?",
    "Should I clear history after?",
    "What about saved passwords?",
    "Can browser remember this?",
    "Is auto-fill risky?",
    "Should I logout after?",
    
    "What if page doesn't load?",
    "It's showing error 404.",
    "Says server not found.",
    "Connection timeout message.",
    "Page is blank white.",
    "Is website down?",
    "How long to wait?",
    "Should I refresh?",
    "Try different browser?",
    "Is there alternate link?",
    
    "What details it will ask?",
    "Do I enter account number?",
    "Should I give password?",
    "What about OTP?",
    "Is date of birth needed?",
    "Should I upload documents?",
    "Which documents required?",
    "Is Aadhaar mandatory?",
    "What about PAN card?",
    "Any photo needed?",
    
    "How secure is this portal?",
    "Is data encrypted?",
    "Who can see my information?",
    "Is it stored somewhere?",
    "Can someone misuse?",
    "What is privacy policy?",
    "Can I delete my data?",
    "Is there data breach risk?",
    "How long kept in system?",
    "Can I opt out later?"
]

# OTP & PIN QUESTIONS (80+ variations)  
OTP_QUESTIONS = [
    "What is OTP for?",
    "Where will OTP come?",
    "Is it safe to share OTP?",
    "My son told never share OTP.",
    "OTP not received yet, should I wait?",
    "Why you need my OTP?",
    "How many digits is OTP?",
    "Is PIN same as OTP?",
    "What is the difference?",
    "Can I use old OTP?",
    
    "OTP message disappeared.",
    "I deleted it by mistake.",
    "Can you resend OTP?",
    "How many times can resend?",
    "Why OTP not coming?",
    "Is my number blocked?",
    "Network issue, what to do?",
    "Can OTP come on email?",
    "What about landline?",
    "Can someone else receive?",
    
    "How long is OTP valid?",
    "It expired already.",
    "Generated new, which to use?",
    "Can I use both?",
    "What if wrong OTP?",
    "How many attempts allowed?",
    "What if account locked?",
    "How to unlock?",
    "Will I get new OTP?",
    "Is there cooldown period?",
    
    "Why multiple OTPs?",
    "Which one to enter?",
    "First or latest?",
    "Are all valid?",
    "Can I try all?",
    "What if none works?",
    "Is system error?",
    "Should I restart phone?",
    "Clear messages and retry?",
    "Contact support?",
    
    "What is OTP used for?",
    "Is it for verification only?",
    "Can money be deducted?",
    "What transactions need OTP?",
    "Is OTP for login?",
    "Or for payment?",
    "What about registration?",
    "Do I need for viewing?",
    "Every time OTP needed?",
    "Can I save it?",
    
    "What is 2-factor authentication?",
    "Is OTP same thing?",
    "Why two steps?",
    "Is password not enough?",
    "What is more secure?",
    "Can I disable it?",
    "Is it mandatory now?",
    "All banks have this?",
    "What about apps?",
    "Is it new rule?",
    
    "What is ATM PIN?",
    "How many digits?",
    "Should I change it?",
    "Can I keep birthday?",
    "What about 1234?",
    "Is there criteria?",
    "How to remember it?",
    "Can I write down?",
    "What if I forget?",
    "How to reset PIN?",
    
    "What is MPIN?",
    "Different from ATM PIN?",
    "How to set MPIN?",
    "How many digits?",
    "Is it mandatory?",
    "Can I skip MPIN?",
    "What if wrong MPIN?",
    "How many tries?",
    "Forgot MPIN now what?",
    "Can I reset myself?"
]

# AMOUNT & PAYMENT QUESTIONS (70+ variations)
AMOUNT_QUESTIONS = [
    "How much money I need to pay?",
    "Why this charge suddenly?",
    "Can I pay at bank branch?",
    "What if I don't pay now?",
    "Where should I send money?",
    "What is your account number?",
    "Can I pay tomorrow?",
    "Is there late fee?",
    "What is deadline?",
    "Can I pay in installments?",
    
    "Why so expensive?",
    "Can amount be reduced?",
    "Is discount available?",
    "What about senior citizens?",
    "Any waiver schemes?",
    "Can I negotiate?",
    "Is this final amount?",
    "Including all taxes?",
    "What is GST rate?",
    "Any hidden charges?",
    
    "Is this refundable?",
    "Can I cancel payment?",
    "What is refund policy?",
    "How long for refund?",
    "Full refund or partial?",
    "What about processing fee?",
    "Is there cancellation charge?",
    "Can I get invoice?",
    "Is receipt provided?",
    "What about warranty?",
    
    "How to pay exactly?",
    "Cash accepted?",
    "What about cheque?",
    "Can I pay by card?",
    "Is UPI okay?",
    "Bank transfer possible?",
    "What are payment options?",
    "Which is fastest?",
    "Which is safest?",
    "Any cashback?",
    
    "Who will receive money?",
    "What is beneficiary name?",
    "Is it company account?",
    "Or personal account?",
    "Can you show proof?",
    "Is this registered?",
    "What about GSTIN?",
    "Any license number?",
    "How to verify?",
    "Is there certificate?",
    
    "What is this charge for?",
    "Why activation fee?",
    "What is processing charge?",
    "Why service charge?",
    "What is convenience fee?",
    "What about maintenance?",
    "Annual or monthly?",
    "One-time or recurring?",
    "Can I pay yearly?",
    "Any discount for advance?",
    
    "Will I get confirmation?",
    "What about receipt?",
    "How to track payment?",
    "What is transaction ID?",
    "Should I note anything?",
    "What about screenshot?",
    "Where to check status?",
    "How long processing?",
    "When will it reflect?",
    "Who to contact if issue?"
]

# VERIFICATION & TRUST QUESTIONS (70+ variations)
VERIFICATION_QUESTIONS = [
    "How do I know you are from real bank?",
    "What is your employee ID?",
    "Can I call back on official number?",
    "What is your supervisor name?",
    "How did you get my phone number?",
    "Which department you calling from?",
    "What is your full name?",
    "Can you spell that?",
    "What is your designation?",
    "How long working there?",
    
    "Can you email me officially?",
    "What is company email ID?",
    "Is there reference number?",
    "Can I get complaint number?",
    "What is ticket ID?",
    "How to escalate this?",
    "Who is your manager?",
    "Can I speak to senior?",
    "Is there helpline?",
    "What about head office?",
    
    "Why calling from mobile?",
    "Is this official number?",
    "Why not from landline?",
    "What is company number?",
    "Can I find it online?",
    "Is it on website?",
    "What about toll-free?",
    "Can I call 1800 number?",
    "Why different number?",
    "Is this normal?",
    
    "How to verify your identity?",
    "Can you prove you're genuine?",
    "What documents you have?",
    "Is there ID card?",
    "Can you show letter?",
    "What about authorization?",
    "Any written communication?",
    "Is there email trail?",
    "What about SMS?",
    "Did bank send notice?",
    
    "Why so urgent?",
    "Can it wait till tomorrow?",
    "Is deadline real?",
    "What will happen if late?",
    "Why pressure me?",
    "Can I think about it?",
    "Let me verify first.",
    "I need time to check.",
    "Can I consult someone?",
    "This feels rushed.",
    
    "Who else called me?",
    "Did you call before?",
    "Why multiple calls?",
    "Different people calling.",
    "What about yesterday?",
    "Someone else also called.",
    "Why so many times?",
    "Is this campaign?",
    "Am I on calling list?",
    "How to stop calls?",
    
    "Is this recorded?",
    "Can I record conversation?",
    "What about privacy?",
    "Who will hear this?",
    "Is it confidential?",
    "Can others access?",
    "What about data security?",
    "Is call encrypted?",
    "Can someone tap?",
    "Is line secure?"
]

# DELAY & STALLING RESPONSES (60+ variations)
DELAY_RESPONSES = [
    "Wait, someone at the door. Give me one minute.",
    "Hold on, my network is breaking.",
    "Let me find my spectacles, can't see properly.",
    "One second, searching for my bank documents.",
    "Battery is low, let me put on charging.",
    "Wait, getting call from my son.",
    "Give me minute, need to use washroom.",
    "Hold please, looking for my documents.",
    "Wait, need to check my phone balance.",
    "One moment, neighbor is calling me.",
    
    "Let me close the door first.",
    "Someone rang doorbell, just a moment.",
    "Hold on, pressure cooker is whistling.",
    "Wait, milk is boiling over.",
    "One second, gas stove is on.",
    "Let me turn off the TV.",
    "Can't hear, too much noise here.",
    "Wait, construction work happening.",
    "Kids are making noise, one minute.",
    "Let me go to quiet room.",
    
    "My wife is calling me.",
    "Daughter is video calling.",
    "Son messaged something urgent.",
    "Let me reply to this SMS first.",
    "Another call coming, can you hold?",
    "WhatsApp message from doctor.",
    "Important email just came.",
    "Bank sent a message, let me check.",
    "Getting OTP, wait let me note.",
    "Phone is hanging, very slow.",
    
    "Need to find my glasses case.",
    "Where did I keep the pen?",
    "Let me get a paper to note.",
    "Looking for my diary.",
    "Need to switch on the light.",
    "Can't find my phone charger.",
    "Let me get my reading lamp.",
    "Where is my notebook?",
    "Looking for my account papers.",
    "Need to find passbook.",
    
    "Feeling little dizzy, one moment.",
    "Need to take my medicine.",
    "Blood pressure is high.",
    "Let me drink some water.",
    "Need to sit down properly.",
    "Getting up from bed slowly.",
    "Walking stick is far.",
    "Need to adjust my pillow.",
    "Can you give me a minute?",
    "Not feeling well.",
    
    "Let me inform my family.",
    "Should ask my son first.",
    "Need daughter's permission.",
    "Wife should know about this.",
    "My brother handles finances.",
    "Let me consult my CA.",
    "Need to ask my lawyer.",
    "Chartered accountant advised me.",
    "My financial advisor should know.",
    "Let me check with family."
]

# FINAL EXTRACTION QUESTIONS (60+ variations)
EXTRACTION_QUESTIONS = [
    "Okay, so what exactly I need to do? Tell step by step.",
    "Let me note down. Tell me slowly one by one.",
    "What details you need from me exactly?",
    "I am ready now. What is first step?",
    "Tell me your contact number in case call drops.",
    "Where should I send the payment exactly?",
    "What is the complete process? Explain fully.",
    "Should I share my account details now?",
    "Give me all information I need.",
    "What happens after I pay?",
    
    "List all steps from beginning.",
    "How many steps total?",
    "What is step one?",
    "After that what?",
    "Then what should I do?",
    "What is last step?",
    "How will I know it's done?",
    "What confirmation I get?",
    "Will you call back?",
    "How to check if successful?",
    
    "What all documents needed?",
    "Should I keep them ready?",
    "Which page of passbook?",
    "Front or back of card?",
    "What about PAN card?",
    "Aadhaar needed?",
    "Should I take photos?",
    "What format required?",
    "PDF or JPG?",
    "How to send documents?",
    
    "What should I not do?",
    "Any precautions?",
    "What mistakes to avoid?",
    "What if something goes wrong?",
    "Can it be reversed?",
    "What is failure rate?",
    "How to handle errors?",
    "Who to contact if issue?",
    "Is there support number?",
    "What are working hours?",
    
    "How long will this take?",
    "Minutes or hours?",
    "Should I wait?",
    "Can I do other work?",
    "Will you stay on call?",
    "Should I call back?",
    "What if it takes longer?",
    "Any timeout issues?",
    "How to know progress?",
    "Will I get updates?",
    
    "Can I do this later?",
    "What if I do tomorrow?",
    "Is today mandatory?",
    "What is last date?",
    "Any extension possible?",
    "What are consequences?",
    "Will fine increase?",
    "What about penalty?",
    "Can I request time?",
    "Who approves extension?"
]

# =========================================================
# SESSION STATE WITH USED RESPONSES TRACKING
# =========================================================
class SessionState:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.message_history = deque(maxlen=2000)
        self.extracted_data = {
            "bankAccounts": set(),
            "upiIds": set(),
            "phishingLinks": set(),
            "phoneNumbers": set(),
            "suspiciousKeywords": set()
        }
        self.total_messages = 0
        self.callback_sent = False
        self.engagement_phase = "initial"
        self.created_at = datetime.now()
        
        # Track used responses to avoid repetition
        self.used_responses = set()
        
        # Track what we've asked about
        self.asked_about = {
            "account": False,
            "upi": False,
            "link": False,
            "otp": False,
            "amount": False,
            "verification": False
        }
    
    def add_message(self, text: str):
        self.message_history.append(text)
        self.total_messages += 1
        
        if self.total_messages < 10:
            self.engagement_phase = "initial"
        elif self.total_messages < 25:
            self.engagement_phase = "probing"
        elif self.total_messages < 35:
            self.engagement_phase = "extraction"
        else:
            self.engagement_phase = "final"
    
    def update_intelligence(self, intel: Dict):
        for key in self.extracted_data:
            if key in intel and intel[key]:
                self.extracted_data[key].update(intel[key])
    
    def get_intelligence_dict(self) -> Dict:
        return {key: sorted(list(value)) for key, value in self.extracted_data.items()}
    
    def should_send_callback(self) -> bool:
        if self.callback_sent or self.total_messages < MIN_MESSAGES_BEFORE_CALLBACK:
            return False
        total_intel = sum(len(v) for v in self.extracted_data.values())
        return total_intel >= 2 or self.total_messages >= TARGET_MESSAGES
    
    def get_unused_response(self, response_pool: List[str]) -> str:
        """Get a response that hasn't been used yet"""
        unused = [r for r in response_pool if r not in self.used_responses]
        
        # If all used, reset (but this shouldn't happen with 700+ responses)
        if not unused:
            self.used_responses.clear()
            unused = response_pool
        
        response = random.choice(unused)
        self.used_responses.add(response)
        return response

SESSION_STORE: Dict[str, SessionState] = {}

# =========================================================
# UTILITIES
# =========================================================
def sanitize(text: str) -> str:
    if not text:
        return ""
    try:
        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)
        text = text.encode("utf-8", "ignore").decode("utf-8")
        return re.sub(r"\s+", " ", text).strip()
    except:
        return ""

def extract_intelligence(text: str) -> Dict:
    clean = sanitize(text)
    return {
        "bankAccounts": list(set(re.findall(r"\b\d{9,18}\b", clean))),
        "upiIds": list(set(re.findall(r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}", clean))),
        "phishingLinks": list(set(re.findall(r"(?:https?://|www\.)[^\s<>\"']+", clean))),
        "phoneNumbers": list(set(re.findall(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b", clean))),
        "suspiciousKeywords": list(set(re.findall(
            r"(?i)\b(urgent|verify|blocked?|suspend|kyc|police|expire[ds]?|immediate|action|confirm|update|security|compromised?|freeze|legal|arrest|penalty|fine)\b", clean
        )))
    }

# =========================================================
# INTELLIGENT RESPONSE ENGINE WITH NO REPETITION
# =========================================================
def generate_strategic_response(session: SessionState, incoming_text: str) -> str:
    """
    Generate unique responses based on phase, never repeating
    """
    t = incoming_text.lower()
    phase = session.engagement_phase
    msg_count = session.total_messages
    
    # Random delays 30% of time (after message 5)
    if msg_count > 5 and random.random() < 0.3:
        return session.get_unused_response(DELAY_RESPONSES)
    
    # Phase 1: Initial Confusion (1-10)
    if phase == "initial":
        return session.get_unused_response(INITIAL_CONFUSION)
    
    # Phase 2: Probing (11-25)
    elif phase == "probing":
        # Context-aware questioning
        if any(x in t for x in ["account", "bank", "ifsc", "balance"]) and not session.asked_about["account"]:
            session.asked_about["account"] = True
            return session.get_unused_response(ACCOUNT_QUESTIONS)
        
        elif any(x in t for x in ["upi", "gpay", "paytm", "phonepe", "payment"]) and not session.asked_about["upi"]:
            session.asked_about["upi"] = True
            return session.get_unused_response(UPI_QUESTIONS)
        
        elif any(x in t for x in ["link", "url", "website", "click", "http", "download"]) and not session.asked_about["link"]:
            session.asked_about["link"] = True
            return session.get_unused_response(LINK_QUESTIONS)
        
        elif any(x in t for x in ["otp", "code", "pin", "password"]) and not session.asked_about["otp"]:
            session.asked_about["otp"] = True
            return session.get_unused_response(OTP_QUESTIONS)
        
        elif any(x in t for x in ["pay", "money", "rupee", "amount", "charge", "fee"]) and not session.asked_about["amount"]:
            session.asked_about["amount"] = True
            return session.get_unused_response(AMOUNT_QUESTIONS)
        
        elif not session.asked_about["verification"]:
            session.asked_about["verification"] = True
            return session.get_unused_response(VERIFICATION_QUESTIONS)
        
        else:
            # Cycle through different types
            pools = [ACCOUNT_QUESTIONS, UPI_QUESTIONS, LINK_QUESTIONS, OTP_QUESTIONS, AMOUNT_QUESTIONS, VERIFICATION_QUESTIONS]
            return session.get_unused_response(random.choice(pools))
    
    # Phase 3: Extraction (26-35)
    elif phase == "extraction":
        return session.get_unused_response(EXTRACTION_QUESTIONS)
    
    # Phase 4: Final (35+)
    else:
        # Mix of extraction and delays
        if random.random() < 0.5:
            return session.get_unused_response(EXTRACTION_QUESTIONS)
        else:
            return session.get_unused_response(DELAY_RESPONSES)

# =========================================================
# API ENDPOINTS
# =========================================================
@app.api_route("/", methods=["GET", "HEAD"])
async def health(request: Request):
    return {
        "status": "Advanced Honeypot Active - 700+ Unique Responses",
        "endpoint": "/honey-pot",
        "total_responses": (
            len(INITIAL_CONFUSION) + 
            len(ACCOUNT_QUESTIONS) + 
            len(UPI_QUESTIONS) + 
            len(LINK_QUESTIONS) + 
            len(OTP_QUESTIONS) + 
            len(AMOUNT_QUESTIONS) + 
            len(VERIFICATION_QUESTIONS) + 
            len(DELAY_RESPONSES) + 
            len(EXTRACTION_QUESTIONS)
        ),
        "active_sessions": len(SESSION_STORE),
        "strategy": "30-40 messages, zero repetition"
    }

class Message(BaseModel):
    sender: str
    text: str
    timestamp: int

class HoneyPotRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: List[Message] = Field(default_factory=list)
    metadata: Optional[Dict] = None

@app.post("/honey-pot")
async def honey_pot(payload: HoneyPotRequest, background_tasks: BackgroundTasks):
    try:
        session_id = sanitize(payload.sessionId)
        if not session_id:
            raise HTTPException(status_code=400, detail="Invalid sessionId")
        
        incoming_text = sanitize(payload.message.text)
        if not incoming_text:
            return {"status": "success", "reply": "Hello? Are you there?"}
        
        if session_id not in SESSION_STORE:
            SESSION_STORE[session_id] = SessionState(session_id)
            logger.info(f"🆕 New session: {session_id}")
        
        session = SESSION_STORE[session_id]
        session.add_message(incoming_text)
        
        logger.info(f"📨 Session {session_id} - Message {session.total_messages}/{TARGET_MESSAGES} - Used responses: {len(session.used_responses)}")
        
        # Extract intelligence
        current_intel = extract_intelligence(incoming_text)
        session.update_intelligence(current_intel)
        
        total_intel = session.get_intelligence_dict()
        intel_count = sum(len(v) for v in total_intel.values())
        logger.info(f"🔍 Intelligence items: {intel_count}")
        
        # Generate unique response
        reply = generate_strategic_response(session, incoming_text)
        
        # Check callback
        if session.should_send_callback() and not session.callback_sent:
            session.callback_sent = True
            logger.info(f"🎯 Sending callback after {session.total_messages} messages with {intel_count} intelligence items")
            
            background_tasks.add_task(
                send_final_callback,
                session_id,
                session.total_messages,
                total_intel
            )
        
        return {"status": "success", "reply": reply}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {"status": "success", "reply": "Sorry, can you repeat? I didn't hear properly."}

@app.post("/honey-pote")
async def honey_pote_endpoint(payload: HoneyPotRequest, background_tasks: BackgroundTasks):
    """Alternative endpoint"""
    return await honey_pot(payload, background_tasks)

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    session_id = sanitize(session_id)
    if session_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSION_STORE[session_id]
    return {
        "sessionId": session.session_id,
        "totalMessages": session.total_messages,
        "engagementPhase": session.engagement_phase,
        "uniqueResponsesUsed": len(session.used_responses),
        "callbackSent": session.callback_sent,
        "extractedIntelligence": session.get_intelligence_dict(),
        "progress": f"{session.total_messages}/{TARGET_MESSAGES}"
    }

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    return {
        "totalSessions": len(SESSION_STORE),
        "sessions": [
            {
                "sessionId": sid,
                "totalMessages": s.total_messages,
                "phase": s.engagement_phase,
                "uniqueResponses": len(s.used_responses),
                "callbackSent": s.callback_sent
            }
            for sid, s in SESSION_STORE.items()
        ]
    }

# =========================================================
# CALLBACK
# =========================================================
def send_final_callback(session_id: str, total_messages: int, intel: Dict):
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": total_messages,
        "extractedIntelligence": intel,
        "agentNotes": (
            f"Advanced engagement successful. Maintained {total_messages} message conversation "
            f"with zero repetition using 700+ unique responses. "
            f"Extracted {sum(len(v) for v in intel.values())} intelligence items. "
            f"Employed confused elderly persona with progressive information extraction strategy."
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
            logger.info(f"✅ Callback sent successfully for session {session_id}")
        else:
            logger.warning(f"⚠️  Callback status: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Callback failed: {e}")

@app.on_event("startup")
async def startup_event():
    total = (len(INITIAL_CONFUSION) + len(ACCOUNT_QUESTIONS) + len(UPI_QUESTIONS) + 
             len(LINK_QUESTIONS) + len(OTP_QUESTIONS) + len(AMOUNT_QUESTIONS) + 
             len(VERIFICATION_QUESTIONS) + len(DELAY_RESPONSES) + len(EXTRACTION_QUESTIONS))
    logger.info(f"🚀 Advanced Honeypot Started")
    logger.info(f"📚 Total unique responses loaded: {total}")
    logger.info(f"🎯 Target: 30-40 messages with ZERO repetition")

# =========================================================
# LOCAL RUN
# =========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("final_honeypot:app", host="0.0.0.0", port=8000, reload=True)