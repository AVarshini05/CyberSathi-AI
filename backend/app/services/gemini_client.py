"""
Gemini AI Client for CCRMS Crime AI Assistant.

Uses the new google.genai SDK.
Provides structured information extraction, validation, confirmation,
timeline generation, and NCRP-style narrative compilation.
"""

import json
import re
import asyncio
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from google import genai
from google.genai import types

from app.core.config import settings
from app.models.ai_session import AISession
from app.models.complaint import ComplaintCategory, ComplaintSubcategory, ComplaintQuestion

logger = logging.getLogger("gemini_client")

# Initialize Gemini client
_client = None
if settings.GEMINI_API_KEY:
    try:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("Gemini client initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize Gemini client: %s", str(e))
else:
    logger.warning("GEMINI_API_KEY is not set — using rule-based fallback.")

# Model fallback chain
_MODEL_CHAIN = ["gemini-2.5-flash", "gemini-2.0-flash", "models/gemini-1.5-flash", "gemini-3.5-flash"]


# ---------------------------------------------------------------------------
# Dynamic System Instructions
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """You are an expert, professional, and empathetic Cybercrime Complaint Intake Officer.
Your goal is to assist a cybercrime victim by extracting accurate information, validating inputs, and maintaining a professional officer persona.
"""


# ---------------------------------------------------------------------------
# Dialogue State Machine Configuration
# ---------------------------------------------------------------------------
VICTIM_FIELDS = [
    {"name": "victim_name", "label": "Full Name", "type": "text", "prompt": "Could you please state your full name?"},
    {"name": "victim_mobile", "label": "Mobile Number", "type": "mobile", "prompt": "Please provide your 10-digit mobile number."},
    {"name": "victim_email", "label": "Email Address", "type": "email", "prompt": "Please provide your email address."},
    {"name": "victim_gender", "label": "Gender", "type": "gender", "prompt": "What is your gender? (Male, Female, or Other)"},
    {"name": "victim_state", "label": "State", "type": "state", "prompt": "Which state do you reside in?"},
    {"name": "victim_address", "label": "Resident Address", "type": "text", "prompt": "Please provide your full residential address."}
]

SUSPECT_FIELDS = [
    {"name": "suspect_name", "label": "Suspect Name", "prompt": "Do you know the name or alias of the suspect?"},
    {"name": "suspect_mobile", "label": "Suspect Mobile Number", "prompt": "Do you have the phone number of the suspect?"},
    {"name": "suspect_email", "label": "Suspect Email Address", "prompt": "Do you have the email address of the suspect?"},
    {"name": "suspect_upi", "label": "Suspect UPI ID", "prompt": "Do you know the UPI ID of the suspect?"},
    {"name": "suspect_social_handle", "label": "Suspect Social Media Handle", "prompt": "Do you have any social media handle (Instagram, Facebook, Telegram) of the suspect?"},
    {"name": "suspect_url", "label": "Suspect Website URL", "prompt": "Do you have any website URL associated with the suspect?"},
    {"name": "suspect_details", "label": "Other Suspect Details", "prompt": "Please share any other known details or descriptions of the suspect."}
]

CRITICAL_FIELDS = ["victim_mobile", "account_number", "utr_number", "transaction_id", "victim_email", "upi_id", "amount", "suspect_mobile", "suspect_upi"]


# ---------------------------------------------------------------------------
# Validation Functions
# ---------------------------------------------------------------------------
def validate_field(field_name: str, value: str) -> bool:
    if not value or value.upper() in ["REVIEW REQUIRED", "UNKNOWN", "SKIP"]:
        return True

    cleaned = value.strip()
    if field_name in ["victim_mobile", "suspect_mobile"]:
        digits = re.sub(r'\D', '', cleaned)
        return len(digits) == 10
    elif field_name == "victim_email" or field_name == "suspect_email":
        return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', cleaned))
    elif field_name in ["upi_id", "suspect_upi", "beneficiary_upi_id"]:
        return '@' in cleaned
    elif field_name == "amount" or field_name == "total_lost":
        digits = re.sub(r'[^\d.]', '', cleaned)
        try:
            float(digits)
            return True
        except ValueError:
            return False
    elif field_name == "account_number":
        digits = re.sub(r'\D', '', cleaned)
        return len(digits) >= 6 and len(digits) <= 18
    elif field_name in ["utr_number", "transaction_id", "tx_hash"]:
        alphanumeric = re.sub(r'[^a-zA-Z0-9]', '', cleaned)
        return len(alphanumeric) >= 6 and len(alphanumeric) <= 24
    return True


# ---------------------------------------------------------------------------
# Indian Language Offline Normalization
# ---------------------------------------------------------------------------
INDIAN_NUMBER_TRANSLATIONS = {
    "పది వేల": "10000", "दस हजार": "10000",
    "ఐదు వేలు": "5000", "पांच हजार": "5000",
    "వేయి": "1000", "हजार": "1000",
    "లక్ష": "100000", "लाख": "100000",
}

INDIAN_PLATFORM_TRANSLATIONS = {
    "ఇంస్టాగ్రామ్": "Instagram", "इंस्टाग्राम": "Instagram",
    "వాట్సాప్": "WhatsApp", "व्हाट्सएप": "WhatsApp",
    "ఫేస్బుక్": "Facebook", "फेसबुक": "Facebook",
    "టెలిగ్రామ్": "Telegram", "टेलीग्राम": "Telegram",
}


# ---------------------------------------------------------------------------
# Helper: Call a specific Gemini model with retry
# ---------------------------------------------------------------------------
async def _call_gemini(model_name: str, prompt: str, system_instruction: str = _SYSTEM_INSTRUCTION) -> Optional[Dict[str, Any]]:
    if not _client:
        return None

    max_retries = 3
    backoff_seconds = 2

    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                _client.models.generate_content,
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    system_instruction=system_instruction,
                    temperature=0.2,
                ),
            )
            data = json.loads(response.text)
            return data
        except json.JSONDecodeError as e:
            logger.error("Gemini [%s] returned invalid JSON: %s", model_name, str(e))
            return None
        except Exception as e:
            err_msg = str(e)
            is_rate_limit = any(kw in err_msg.lower() for kw in ["429", "resourceexhausted", "quota", "rate limit"])
            if is_rate_limit and attempt < max_retries - 1:
                logger.warning("Gemini [%s] rate-limited. Retrying in %ds...", model_name, backoff_seconds)
                await asyncio.sleep(backoff_seconds)
                backoff_seconds *= 2
                continue
            raise
    return None


# ---------------------------------------------------------------------------
# Offline Fallback Dialog Controllers
# ---------------------------------------------------------------------------
def _offline_classify_crime(message: str) -> Dict[str, Any]:
    full_text = message.lower()
    cat = None
    sub = None

    if any(kw in full_text for kw in ["instagram", "facebook", "twitter", "snapchat", "linkedin"]):
        cat = "Other Cyber Crime"
        sub = "Social Media Hacking"
        if any(kw in full_text for kw in ["fake", "impersonat", "profile"]):
            sub = "Fake Profile / Impersonation"
    elif any(kw in full_text for kw in ["upi", "phonepe", "gpay", "google pay", "paytm", "ybl"]):
        cat = "Financial Fraud"
        sub = "UPI Fraud"
    elif any(kw in full_text for kw in ["credit card", "debit card", "atm", "card cloned"]):
        cat = "Financial Fraud"
        sub = "Debit/Credit Card Fraud"
    elif any(kw in full_text for kw in ["net banking", "internet banking", "neft", "imps", "utr"]):
        cat = "Financial Fraud"
        sub = "Internet Banking Fraud"
    elif any(kw in full_text for kw in ["investment", "trading", "stock", "scam"]):
        cat = "Financial Fraud"
        sub = "Investment/Trading Scam"
    elif any(kw in full_text for kw in ["loan app", "instant loan"]):
        cat = "Financial Fraud"
        sub = "Loan App Fraud"
    elif any(kw in full_text for kw in ["crypto", "bitcoin", "ethereum", "usdt"]):
        cat = "Financial Fraud"
        sub = "Cryptocurrency Fraud"
    elif any(kw in full_text for kw in ["stalking", "harassment"]):
        cat = "Women and Children Related Crime"
        sub = "Cyber Stalking / Online Harassment"
    elif any(kw in full_text for kw in ["blackmail", "sextortion"]):
        cat = "Women and Children Related Crime"
        sub = "Blackmail / Sextortion"
    elif any(kw in full_text for kw in ["child exploitation", "csam", "obscene"]):
        cat = "Women and Children Related Crime"
        sub = "Child Exploitation / Obscene Content"
    elif any(kw in full_text for kw in ["email", "gmail"]):
        cat = "Other Cyber Crime"
        sub = "Email Hacking"
    elif any(kw in full_text for kw in ["ransomware", "malware", "encrypt"]):
        cat = "Other Cyber Crime"
        sub = "Ransomware / Malware Attack"

    return {"category": cat, "subcategory": sub}


def _offline_extract_field(field_name: str, field_type: str, message: str) -> Optional[str]:
    text = message.strip()
    lower = text.lower()

    if lower in ["skip", "no", "i don't know", "dont know", "not sure", "unknown"]:
        return "skip"

    # Multilingual mapping fallbacks
    for native_word, eng_word in INDIAN_NUMBER_TRANSLATIONS.items():
        if native_word in text:
            text = text.replace(native_word, eng_word)
    for native_plat, eng_plat in INDIAN_PLATFORM_TRANSLATIONS.items():
        if native_plat in text:
            return eng_plat

    if field_type == "mobile" or field_name == "suspect_mobile":
        matches = re.findall(r'\b\d{10}\b', text)
        return matches[0] if matches else None
    elif field_type == "email" or field_name == "suspect_email":
        matches = re.findall(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', text)
        return matches[0] if matches else None
    elif field_name in ["upi_id", "suspect_upi", "beneficiary_upi_id"]:
        matches = re.findall(r'\b[a-zA-Z0-9.-]+@[a-zA-Z]{3,}\b', text)
        return matches[0] if matches else None
    elif field_name == "amount" or field_name == "total_lost":
        matches = re.findall(r'\b\d+\b', text)
        return matches[0] if matches else None
    elif field_name == "account_number":
        matches = re.findall(r'\b\d{6,18}\b', text)
        return matches[0] if matches else None
    elif field_name in ["utr_number", "transaction_id"]:
        matches = re.findall(r'\b[A-Za-z0-9]{6,22}\b', text)
        return matches[0] if matches else None
    elif field_type == "gender":
        if "female" in lower or "మహిళ" in lower or "महिला" in lower:
            return "Female"
        if "male" in lower or "పురుషుడు" in lower or "पुरुष" in lower:
            return "Male"
        return "Other"
    elif field_type == "state":
        states = ["Andhra Pradesh", "Assam", "Bihar", "Delhi", "Gujarat", "Karnataka", "Kerala", "Maharashtra", "Tamil Nadu", "Telangana", "Uttar Pradesh", "West Bengal"]
        for st in states:
            if st.lower() in lower:
                return st
        return None

    return text if len(text) > 0 else None


# ---------------------------------------------------------------------------
# Dialogue Manager Turn Processing
# ---------------------------------------------------------------------------
def _get_current_prompt(db: Session, step: int, current_field: Optional[str], session: AISession) -> str:
    if step == 1:
        return "Could you please describe the incident in your own words?"
    elif step == 2:
        if current_field == "is_anonymous":
            return "You have the option to file this complaint anonymously. Would you like to file anonymously? (Yes/No)"
        for vf in VICTIM_FIELDS:
            if vf["name"] == current_field:
                return vf["prompt"]
        return "Please provide your details."
    elif step == 3:
        if current_field:
            q_obj = db.query(ComplaintQuestion).filter(
                ComplaintQuestion.subcategory_id == session.detected_subcategory_id,
                ComplaintQuestion.field_name == current_field
            ).first()
            if q_obj:
                return f"{q_obj.field_label}?"
        return "Please provide the incident details."
    elif step == 4:
        for sf in SUSPECT_FIELDS:
            if sf["name"] == current_field:
                return sf["prompt"]
        return "Please provide suspect details."
    elif step == 5:
        if current_field == "evidence_screenshots":
            return "Do you have any screenshots or chat history of the incident?"
        elif current_field == "evidence_bank_statement":
            return "Do you have any bank statement or transaction receipt proof?"
        elif current_field == "evidence_email_call":
            return "Do you have any email communications or call recordings?"
        return "Do you have any evidence to upload?"
    elif step == 6:
        return "Would you like to modify any information before proceeding to submission? (Yes/No)"
    return "Please continue."


# ---------------------------------------------------------------------------
# Dialogue Manager Turn Processing
# ---------------------------------------------------------------------------
async def process_dialogue_turn(
    db: Session,
    session: AISession,
    user_message: str,
    confidence: float = 1.0,
    user_logged_in: bool = False
) -> Dict[str, Any]:
    collected = dict(session.collected_data or {})
    
    # Maintain Officer memory
    victim_name = collected.get("victim_name", "")
    greeting_prefix = f"Thank you, {victim_name}. " if (victim_name and victim_name != "REVIEW REQUIRED") else ""

    # Emergency escalation check
    escalate = False
    lower_msg = user_message.lower()
    if any(kw in lower_msg for kw in ["suicide", "kill myself", "harm myself", "ongoing theft", "child abuse", "ransomware", "sextortion", "blackmail"]):
        escalate = True

    response_text = ""
    is_complete = False
    duplicate_warning = None

    # Determine priority
    detected_cat = None
    detected_sub = None
    cat_obj = db.query(ComplaintCategory).filter(ComplaintCategory.id == session.detected_category_id).first()
    sub_obj = db.query(ComplaintSubcategory).filter(ComplaintSubcategory.id == session.detected_subcategory_id).first()
    if cat_obj: detected_cat = cat_obj.name
    if sub_obj: detected_sub = sub_obj.name

    step = int(collected.get("step", 1))
    current_field = collected.get("current_field")
    attempt_count = int(collected.get("attempt_count", 0))
    sub_state = collected.get("sub_state")

    # Check if user message is an informational question
    is_q = False
    q_answer = ""
    if _client and user_message and user_message.strip() != "/resume":
        q_prompt = (
            f"You are a helpful Cybercrime Complaint Officer.\n"
            f"Determine if the user's message is an informational question about terminology (like UTR, transaction ID, bank statements, evidence) or how-to help, rather than a direct answer to the intake field.\n"
            f"User message: '{user_message}'\n\n"
            f"Return JSON:\n"
            f"{{\n"
            f'  "is_question": true,\n'
            f'  "answer": "Empathic, clear, short explanation answering their question in the same language they asked"\n'
            f"}} or if it is not a question, return {{\"is_question\": false}}"
        )
        try:
            res = await _call_gemini(_MODEL_CHAIN[0], q_prompt)
            if res and res.get("is_question"):
                is_q = True
                q_answer = res.get("answer")
        except Exception:
            pass

    if not is_q and user_message and user_message.strip() != "/resume":
        # Simple offline keyword detection for common questions
        if "what is utr" in lower_msg or "utr number" in lower_msg:
            is_q = True
            q_answer = "A UTR (Unique Transaction Reference) number is a 22-digit or 16-digit unique code generated by banks for IMPS, NEFT, or RTGS transactions to trace your payment."
        elif "transaction id" in lower_msg or "txn id" in lower_msg:
            is_q = True
            q_answer = "A Transaction ID is a unique reference number generated by UPI apps (like GPay, PhonePe, Paytm) or banks for each transaction to identify the specific transfer."
        elif "bank statement" in lower_msg or "where can i find" in lower_msg:
            is_q = True
            q_answer = "You can download your bank statement from your bank's mobile app, internet banking portal, or by visiting your branch."
        elif "what is evidence" in lower_msg or "what should i upload" in lower_msg or "screenshot" in lower_msg:
            is_q = True
            q_answer = "Evidence includes screenshots of chats, suspect profile pages, payment receipt PDFs, bank statements showing the debit, and email headers."

    if is_q:
        current_prompt = _get_current_prompt(db, step, current_field, session)
        response_text = f"{q_answer}\n\nLet's continue with the filing process: {current_prompt}"
        
        # Calculate Completeness scores
        cat_comp = 100 if session.detected_subcategory_id else 0
        if collected.get("is_anonymous"):
            vic_comp = 100
        else:
            vic_filled = sum(1 for vf in VICTIM_FIELDS if collected.get(vf["name"]))
            vic_comp = int((vic_filled / len(VICTIM_FIELDS)) * 100)
        
        dyn_questions = collected.get("dynamic_questions", [])
        if dyn_questions:
            inc_filled = sum(1 for q in dyn_questions if collected.get(q))
            inc_comp = int((inc_filled / len(dyn_questions)) * 100)
        else:
            inc_comp = 0
            
        sus_filled = sum(1 for sf in SUSPECT_FIELDS if collected.get(sf["name"]))
        sus_comp = int((sus_filled / len(SUSPECT_FIELDS)) * 100)

        ev_map = collected.get("evidence_map", {})
        ev_comp = 20
        if ev_map.get("Screenshot"): ev_comp = 50
        if ev_map.get("Screenshot") and ev_map.get("Bank Statement"): ev_comp = 80
        if ev_map.get("Screenshot") and ev_map.get("Bank Statement") and ev_map.get("Audio"): ev_comp = 100

        overall = int((cat_comp * 0.1) + (vic_comp * 0.2) + (inc_comp * 0.3) + (sus_comp * 0.2) + (ev_comp * 0.2))

        progress_breakdown = {
            "category": cat_comp,
            "victim": vic_comp,
            "incident": inc_comp,
            "suspect": sus_comp,
            "evidence": ev_comp,
            "overall": overall
        }

        return {
            "response": response_text,
            "detected_category": detected_cat,
            "detected_subcategory": detected_sub,
            "quality_score": overall,
            "is_high_priority": overall >= 80 or escalate or (detected_cat == "Women and Children Related Crime"),
            "is_complete": False,
            "step": step,
            "progress_breakdown": progress_breakdown,
            "duplicate_warning": None
        }

    # Check for authentication resume command
    if user_message == "/resume" or user_message.lower() == "resume":
        if session.detected_category_id and session.detected_subcategory_id and user_logged_in:
            collected["step"] = 2
            collected["attempt_count"] = 0
            collected.pop("sub_state", None)
            
            cat_obj = db.query(ComplaintCategory).filter(ComplaintCategory.id == session.detected_category_id).first()
            sub_obj = db.query(ComplaintSubcategory).filter(ComplaintSubcategory.id == session.detected_subcategory_id).first()
            detected_cat = cat_obj.name if cat_obj else ""
            detected_sub = sub_obj.name if sub_obj else ""

            if cat_obj and cat_obj.code == 'WC':
                collected["current_field"] = "is_anonymous"
                response_text = (
                    f"Welcome back. Let us continue your complaint.\n\n"
                    f"Since this relates to Women and Child safety, priority mode is activated.\n"
                    f"You have the option to file this complaint anonymously. Would you like to file anonymously? (Yes/No)"
                )
            else:
                collected["current_field"] = "victim_name"
                response_text = (
                    f"Welcome back. Let us continue your complaint.\n\n"
                    f"Let's record your details. What is your full name?"
                )
            
            collected["step"] = 2
            session.collected_data = collected
            db.commit()
            
            progress_breakdown = {
                "category": 100,
                "victim": 0,
                "incident": 0,
                "suspect": 0,
                "evidence": 20,
                "overall": 20
            }
            return {
                "response": response_text,
                "detected_category": detected_cat,
                "detected_subcategory": detected_sub,
                "quality_score": 20,
                "is_high_priority": cat_obj.code == 'WC' if cat_obj else False,
                "is_complete": False,
                "step": 2,
                "progress_breakdown": progress_breakdown,
                "duplicate_warning": None
            }

    # -----------------------------------------------------------------------
    # sub_state: CONFIRMING_FIELD
    # -----------------------------------------------------------------------
    if sub_state == "CONFIRMING_FIELD":
        unconfirmed_name = collected.get("unconfirmed_field_name")
        unconfirmed_value = collected.get("unconfirmed_field_value")

        confirmed = False
        new_val = None

        if _client:
            prompt = (
                f"Determine if the user's message is confirming or rejecting/denying the statement.\n"
                f"User's message: '{user_message}'\n\n"
                f"Return a JSON object: {{\"confirmed\": true}} if they confirm (e.g. yes, correct, right, yeah, ha, అవును, हाँ).\n"
                f"Return {{\"confirmed\": false}} if they reject/deny (e.g. no, incorrect, wrong, కాదు, नहीं).\n"
                f"If they say 'no' but immediately provide a new value in the same message, return: {{\"confirmed\": false, \"new_value\": \"extracted_new_value\"}}."
            )
            try:
                res = await _call_gemini(_MODEL_CHAIN[0], prompt)
                if res:
                    confirmed = bool(res.get("confirmed"))
                    new_val = res.get("new_value")
            except Exception:
                pass

        if not confirmed and not new_val:
            # Rule-based fallback for confirmation
            yes_kws = ["yes", "correct", "yeah", "ha", "अవును", "हाँ", "correct", "right", "true"]
            no_kws = ["no", "incorrect", "wrong", "కాదు", "नहीं", "false"]
            if any(k in lower_msg for k in yes_kws):
                confirmed = True
            elif any(k in lower_msg for k in no_kws):
                confirmed = False
                # Attempt to extract new number/code if present
                nums = re.findall(r'\b\d{4,}\b', user_message)
                if nums:
                    new_val = nums[0]

        if confirmed:
            collected[unconfirmed_name] = unconfirmed_value
            collected.pop("sub_state", None)
            collected.pop("unconfirmed_field_name", None)
            collected.pop("unconfirmed_field_value", None)
            collected["attempt_count"] = 0
            
            # Transition forward
            response_text = "Thank you. Finalized."
            # Clear field state so we can advance
            current_field = None
        else:
            collected.pop("sub_state", None)
            collected.pop("unconfirmed_field_name", None)
            collected.pop("unconfirmed_field_value", None)
            
            if new_val:
                # User provided a correction! Cycle back into confirmation
                # Find label for the field
                label = unconfirmed_name
                for vf in VICTIM_FIELDS:
                    if vf["name"] == unconfirmed_name: label = vf["label"]
                if unconfirmed_name in SUSPECT_FIELDS:
                    for sf in SUSPECT_FIELDS:
                        if sf["name"] == unconfirmed_name: label = sf["label"]
                
                # Digit space for numbers
                spaced = " ".join(list(new_val)) if re.match(r'^\d+$', new_val) else new_val
                response_text = f"I apologize. I heard your {label} as: {spaced}. Is that correct?"
                collected["sub_state"] = "CONFIRMING_FIELD"
                collected["unconfirmed_field_name"] = unconfirmed_name
                collected["unconfirmed_field_value"] = new_val
            else:
                # Increment attempts
                attempt_count += 1
                collected["attempt_count"] = attempt_count
                if attempt_count >= 3:
                    collected[unconfirmed_name] = "REVIEW REQUIRED"
                    collected["attempt_count"] = 0
                    current_field = None
                    response_text = f"I understand. Let's record this as REVIEW REQUIRED and move forward."
                else:
                    label = unconfirmed_name
                    for vf in VICTIM_FIELDS:
                        if vf["name"] == unconfirmed_name: label = vf["label"]
                    response_text = f"I apologize. Could you please state your {label} again?"

    # -----------------------------------------------------------------------
    # Step 1: Crime Classification
    # -----------------------------------------------------------------------
    elif step == 1:
        cat = None
        sub = None
        clarification = ""

        if _client:
            prompt = (
                f"Analyze the user message to classify the crime category and subcategory.\n"
                f"User Message: '{user_message}'\n\n"
                f"Categories:\n"
                f"1. Financial Fraud (Subcategories: UPI Fraud, Internet Banking Fraud, Debit/Credit Card Fraud, Investment/Trading Scam, Loan App Fraud, Cryptocurrency Fraud)\n"
                f"2. Other Cyber Crime (Subcategories: Social Media Hacking, Fake Profile / Impersonation, Email Hacking, Ransomware / Malware Attack)\n"
                f"3. Women and Children Related Crime (Subcategories: Cyber Stalking / Online Harassment, Blackmail / Sextortion, Child Exploitation / Obscene Content)\n\n"
                f"Return JSON:\n"
                f"{{\n"
                f'  "category": "Category name or null if unclear",\n'
                f'  "subcategory": "Subcategory name or null if unclear",\n'
                f'  "clarification": "Follow-up question to determine categories if unclear"\n'
                f"}}"
            )
            try:
                res = await _call_gemini(_MODEL_CHAIN[0], prompt)
                if res:
                    cat = res.get("category")
                    sub = res.get("subcategory")
                    clarification = res.get("clarification")
            except Exception:
                pass

        if not cat or not sub:
            # Offline fallback classification
            result = _offline_classify_crime(user_message)
            cat = result["category"]
            sub = result["subcategory"]

        if cat and sub:
            category = db.query(ComplaintCategory).filter(ComplaintCategory.name == cat).first()
            subcategory = db.query(ComplaintSubcategory).filter(
                ComplaintSubcategory.name == sub,
                ComplaintSubcategory.category_id == category.id
            ).first()

            if category and subcategory:
                session.detected_category_id = category.id
                session.detected_subcategory_id = subcategory.id
                detected_cat = category.name
                detected_sub = subcategory.name

                if not user_logged_in:
                    collected["step"] = 1
                    response_text = (
                        f"I have identified this as {detected_sub} under {detected_cat}.\n\n"
                        f"Before filing the complaint, please sign in or create an account."
                    )
                    session.collected_data = collected
                    db.commit()
                    
                    return {
                        "response": response_text,
                        "detected_category": detected_cat,
                        "detected_subcategory": detected_sub,
                        "quality_score": 10,
                        "is_high_priority": category.code == 'WC',
                        "is_complete": False,
                        "step": 1,
                        "requires_auth": True,
                        "progress_breakdown": {
                            "category": 100,
                            "victim": 0,
                            "incident": 0,
                            "suspect": 0,
                            "evidence": 20,
                            "overall": 10
                        },
                        "duplicate_warning": None
                    }
                else:
                    # Check priority WC
                    if category.code == 'WC':
                        collected["step"] = 2
                        collected["current_field"] = "is_anonymous"
                        response_text = (
                            f"Based on your description, I have classified this incident as {detected_sub} under {detected_cat}.\n\n"
                            f"Since this relates to Women and Child safety, priority mode is activated.\n"
                            f"You have the option to file this complaint anonymously. Would you like to file anonymously? (Yes/No)"
                        )
                    else:
                        collected["step"] = 2
                        collected["current_field"] = "victim_name"
                        response_text = (
                            f"Based on your description, I have classified this incident as {detected_sub} under {detected_cat}.\n\n"
                            f"I am now navigating to the Victim Information page. Let's record your details. What is your full name?"
                        )
            else:
                response_text = clarification or "Could you please describe the incident in more detail? For example, was it a card cloning, a UPI transfer, or a social media hack?"
        else:
            response_text = clarification or "Could you please describe the incident in more detail? For example, was it a card cloning, a UPI transfer, or a social media hack?"

    # -----------------------------------------------------------------------
    # Step 2: Victim Information
    # -----------------------------------------------------------------------
    elif step == 2:
        # Check anonymous mode toggle first
        if current_field == "is_anonymous":
            val = _offline_extract_field("is_anonymous", "text", user_message)
            if val and val.lower() in ["yes", "y", "true", "అవును", "हाँ"]:
                collected["is_anonymous"] = True
                # Jump straight to Step 3
                collected["step"] = 3
                # Load dynamic questions from DB
                questions = db.query(ComplaintQuestion).filter(ComplaintQuestion.subcategory_id == session.detected_subcategory_id).all()
                if questions:
                    collected["dynamic_questions"] = [q.field_name for q in questions]
                    collected["dynamic_questions_index"] = 0
                    collected["current_field"] = questions[0].field_name
                    # Find label for first dynamic question
                    response_text = f"Anonymous mode activated. Skipping victim profile.\n\nNavigating to Incident Details page. {questions[0].field_label}?"
                else:
                    collected["step"] = 4
                    collected["current_field"] = "suspect_name"
                    response_text = f"Anonymous mode activated. Skipping victim profile.\n\nNavigating to Suspect Details page. Do you know the name or alias of the suspect?"
            else:
                collected["is_anonymous"] = False
                collected["current_field"] = "victim_name"
                response_text = "Understood. We will record your details. Let's start with: What is your full name?"
        else:
            # Find field details
            field_def = None
            field_idx = 0
            for i, vf in enumerate(VICTIM_FIELDS):
                if vf["name"] == current_field:
                    field_def = vf
                    field_idx = i
                    break

            if field_def:
                extracted = None
                if _client:
                    prompt = (
                        f"Extract the value for '{field_def['name']}' (Type: '{field_def['type']}', Label: '{field_def['label']}') from the user's message.\n"
                        f"User's message: '{user_message}'\n\n"
                        f"Rules:\n"
                        f"- Extract the value and translate/normalize it to English if in an Indian language.\n"
                        f"- If they refuse, say skip, or say they do not know, return {{\"value\": \"skip\"}}.\n"
                        f"Return JSON:\n"
                        f"{{\n"
                        f'  "value": "extracted_value_or_null"\n'
                        f"}}"
                    )
                    try:
                        res = await _call_gemini(_MODEL_CHAIN[0], prompt)
                        if res:
                            extracted = res.get("value")
                    except Exception:
                        pass

                if not extracted:
                    extracted = _offline_extract_field(field_def["name"], field_def["type"], user_message)

                if extracted:
                    # Validate
                    if extracted == "skip":
                        collected[field_def["name"]] = "REVIEW REQUIRED"
                        collected["attempt_count"] = 0
                        current_field = None # Trigger advance
                    elif validate_field(field_def["name"], extracted):
                        # Trigger confirmation loop for critical fields
                        if field_def["name"] in CRITICAL_FIELDS and confidence < 0.8:
                            # Digit space numbers for speech
                            spaced = " ".join(list(extracted)) if re.match(r'^\d+$', extracted) else extracted
                            response_text = f"I heard your {field_def['label']} as: {spaced}. Is that correct?"
                            collected["sub_state"] = "CONFIRMING_FIELD"
                            collected["unconfirmed_field_name"] = field_def["name"]
                            collected["unconfirmed_field_value"] = extracted
                        else:
                            collected[field_def["name"]] = extracted
                            collected["attempt_count"] = 0
                            current_field = None # Trigger advance
                    else:
                        # Invalid format
                        attempt_count += 1
                        collected["attempt_count"] = attempt_count
                        if attempt_count >= 3:
                            collected[field_def["name"]] = "REVIEW REQUIRED"
                            collected["attempt_count"] = 0
                            current_field = None # Advance
                            response_text = f"The input format is incorrect. Recording as REVIEW REQUIRED and moving on."
                        else:
                            response_text = f"The {field_def['label']} format appears invalid. Could you please provide it again?"
                else:
                    # Not found
                    attempt_count += 1
                    collected["attempt_count"] = attempt_count
                    if attempt_count >= 3:
                        collected[field_def["name"]] = "REVIEW REQUIRED"
                        collected["attempt_count"] = 0
                        current_field = None # Advance
                        response_text = f"No details found. Recording as REVIEW REQUIRED and moving on."
                    else:
                        response_text = f"Could you please provide your {field_def['label']}?"

            # If current_field cleared, we advance
            if current_field is None:
                next_idx = field_idx + 1
                if next_idx < len(VICTIM_FIELDS):
                    next_field = VICTIM_FIELDS[next_idx]
                    collected["current_field"] = next_field["name"]
                    if not response_text:
                        response_text = f"{greeting_prefix}Next question: {next_field['prompt']}"
                    else:
                        response_text = f"{response_text}\n\n{next_field['prompt']}"
                else:
                    # Victim info complete! Move to step 3
                    collected["step"] = 3
                    questions = db.query(ComplaintQuestion).filter(ComplaintQuestion.subcategory_id == session.detected_subcategory_id).all()
                    if questions:
                        collected["dynamic_questions"] = [q.field_name for q in questions]
                        collected["dynamic_questions_index"] = 0
                        collected["current_field"] = questions[0].field_name
                        response_text = f"Victim details complete.\n\nNavigating to Incident Details page. {questions[0].field_label}?"
                    else:
                        collected["step"] = 4
                        collected["current_field"] = "suspect_name"
                        response_text = f"Victim details complete.\n\nNavigating to Suspect Details page. Do you know the name or alias of the suspect?"

    # -----------------------------------------------------------------------
    # Step 3: Incident Details (Dynamic Questionnaire)
    # -----------------------------------------------------------------------
    elif step == 3:
        dyn_questions = collected.get("dynamic_questions", [])
        q_idx = int(collected.get("dynamic_questions_index", 0))

        if q_idx < len(dyn_questions):
            q_name = dyn_questions[q_idx]
            q_obj = db.query(ComplaintQuestion).filter(
                ComplaintQuestion.subcategory_id == session.detected_subcategory_id,
                ComplaintQuestion.field_name == q_name
            ).first()

            if q_obj:
                extracted = None
                if _client:
                    prompt = (
                        f"Extract the value for '{q_obj.field_name}' (Label: '{q_obj.field_label}') from the user's message.\n"
                        f"User's message: '{user_message}'\n\n"
                        f"Rules:\n"
                        f"- Extract and translate/normalize value to English if in native Indian languages.\n"
                        f"- If they do not know or refuse or say skip, return {{\"value\": \"skip\"}}.\n"
                        f"Return JSON:\n"
                        f"{{\n"
                        f'  "value": "extracted_value_or_null"\n'
                        f"}}"
                    )
                    try:
                        res = await _call_gemini(_MODEL_CHAIN[0], prompt)
                        if res:
                            extracted = res.get("value")
                    except Exception:
                        pass

                if not extracted:
                    extracted = _offline_extract_field(q_obj.field_name, q_obj.field_type, user_message)

                if extracted:
                    if extracted == "skip":
                        collected[q_obj.field_name] = "REVIEW REQUIRED"
                        collected["attempt_count"] = 0
                        q_idx += 1
                        collected["dynamic_questions_index"] = q_idx
                    elif validate_field(q_obj.field_name, extracted):
                        # Duplicate Scan check on critical fields (UTR / Transaction ID)
                        if q_obj.field_name in ["utr_number", "transaction_id", "tx_hash"]:
                            from app.models.complaint import ComplaintAnswer, Complaint
                            dup = db.query(Complaint).join(ComplaintAnswer).filter(
                                ComplaintAnswer.value == str(extracted)
                            ).first()
                            if dup:
                                duplicate_warning = f"A complaint matching UTR/Transaction ID {extracted} already exists in the system (Ack: {dup.acknowledgement_number})."
                        
                        # Trigger confirmation loop
                        if q_obj.field_name in CRITICAL_FIELDS:
                            spaced = " ".join(list(extracted)) if re.match(r'^\d+$', extracted) else extracted
                            response_text = f"I heard your {q_obj.field_label} as: {spaced}. Is that correct?"
                            collected["sub_state"] = "CONFIRMING_FIELD"
                            collected["unconfirmed_field_name"] = q_obj.field_name
                            collected["unconfirmed_field_value"] = extracted
                        else:
                            collected[q_obj.field_name] = extracted
                            collected["attempt_count"] = 0
                            q_idx += 1
                            collected["dynamic_questions_index"] = q_idx
                    else:
                        attempt_count += 1
                        collected["attempt_count"] = attempt_count
                        if attempt_count >= 3:
                            collected[q_obj.field_name] = "REVIEW REQUIRED"
                            collected["attempt_count"] = 0
                            q_idx += 1
                            collected["dynamic_questions_index"] = q_idx
                            response_text = f"Format invalid. Recording as REVIEW REQUIRED and advancing."
                        else:
                            response_text = f"The {q_obj.field_label} appears invalid. Could you please provide it again?"
                else:
                    attempt_count += 1
                    collected["attempt_count"] = attempt_count
                    if attempt_count >= 3:
                        collected[q_obj.field_name] = "REVIEW REQUIRED"
                        collected["attempt_count"] = 0
                        q_idx += 1
                        collected["dynamic_questions_index"] = q_idx
                        response_text = f"No value extracted. Recording as REVIEW REQUIRED."
                    else:
                        response_text = f"Please provide the {q_obj.field_label}."

            # Advance check
            if q_idx < len(dyn_questions):
                next_q_name = dyn_questions[q_idx]
                next_q_obj = db.query(ComplaintQuestion).filter(
                    ComplaintQuestion.subcategory_id == session.detected_subcategory_id,
                    ComplaintQuestion.field_name == next_q_name
                ).first()
                if next_q_obj:
                    collected["current_field"] = next_q_name
                    if not response_text:
                        response_text = f"{next_q_obj.field_label}?"
                    else:
                        response_text = f"{response_text}\n\n{next_q_obj.field_label}?"
            else:
                # Incident questionnaire complete!
                collected["step"] = 4
                collected["current_field"] = "suspect_name"
                if not response_text:
                    response_text = f"Incident details recorded. Navigating to Suspect Details page.\n\nDo you know the name or alias of the suspect?"
                else:
                    response_text = f"{response_text}\n\nIncident details recorded. Navigating to Suspect Details page. Do you know the name or alias of the suspect?"

    # -----------------------------------------------------------------------
    # Step 4: Suspect Details
    # -----------------------------------------------------------------------
    elif step == 4:
        field_idx = 0
        field_def = None
        for i, sf in enumerate(SUSPECT_FIELDS):
            if sf["name"] == current_field:
                field_def = sf
                field_idx = i
                break

        if field_def:
            extracted = None
            if _client:
                prompt = (
                    f"Extract suspect detail '{field_def['name']}' from user message.\n"
                    f"User Message: '{user_message}'\n\n"
                    f"Return JSON: {{\"value\": \"extracted_value_or_null\"}}.\n"
                    f"If they refuse, say 'skip', say 'no' or they do not know, return {{\"value\": \"UNKNOWN\"}}."
                )
                try:
                    res = await _call_gemini(_MODEL_CHAIN[0], prompt)
                    if res:
                        extracted = res.get("value")
                except Exception:
                    pass

            if not extracted:
                extracted = _offline_extract_field(field_def["name"], "text", user_message)

            if extracted:
                if extracted.upper() in ["UNKNOWN", "SKIP", "NO"]:
                    collected[field_def["name"]] = "UNKNOWN"
                    current_field = None # Advance
                elif validate_field(field_def["name"], extracted):
                    # Trigger confirmation loop
                    if field_def["name"] in CRITICAL_FIELDS:
                        spaced = " ".join(list(extracted)) if re.match(r'^\d+$', extracted) else extracted
                        response_text = f"I heard the suspect {field_def['label']} as: {spaced}. Is that correct?"
                        collected["sub_state"] = "CONFIRMING_FIELD"
                        collected["unconfirmed_field_name"] = field_def["name"]
                        collected["unconfirmed_field_value"] = extracted
                    else:
                        collected[field_def["name"]] = extracted
                        current_field = None # Advance
                else:
                    collected[field_def["name"]] = "UNKNOWN"
                    current_field = None # Advance
            else:
                collected[field_def["name"]] = "UNKNOWN"
                current_field = None # Advance

        # Advance check
        if current_field is None:
            next_idx = field_idx + 1
            if next_idx < len(SUSPECT_FIELDS):
                next_field = SUSPECT_FIELDS[next_idx]
                collected["current_field"] = next_field["name"]
                if not response_text:
                    response_text = next_field["prompt"]
                else:
                    response_text = f"{response_text}\n\n{next_field['prompt']}"
            else:
                # Suspect details complete! Move to step 5
                collected["step"] = 5
                collected["current_field"] = "evidence_screenshots"
                if not response_text:
                    response_text = "Suspect details complete.\n\nNavigating to Evidence Upload page. Do you have any screenshots or chat history of the incident?"
                else:
                    response_text = f"{response_text}\n\nSuspect details complete.\n\nNavigating to Evidence Upload page. Do you have any screenshots or chat history of the incident?"

    # -----------------------------------------------------------------------
    # Step 5: Evidence Upload Questionnaire
    # -----------------------------------------------------------------------
    elif step == 5:
        # We ask 3 simple evidence questions
        # - evidence_screenshots
        # - evidence_bank_statement
        # - evidence_email_call
        evidence_map = collected.get("evidence_map", {
            "Screenshot": False, "Chat": False, "Audio": False, "Video": False, "PDF": False, "Bank Statement": False
        })

        if current_field == "evidence_screenshots":
            if any(kw in lower_msg for kw in ["yes", "yeah", "ha", "అవును", "हाँ"]):
                evidence_map["Screenshot"] = True
                evidence_map["Chat"] = True
            collected["evidence_map"] = evidence_map
            collected["current_field"] = "evidence_bank_statement"
            response_text = "Do you have any bank statement or transaction receipt proof?"
        elif current_field == "evidence_bank_statement":
            if any(kw in lower_msg for kw in ["yes", "yeah", "ha", "అవును", "हाँ"]):
                evidence_map["Bank Statement"] = True
                evidence_map["PDF"] = True
            collected["evidence_map"] = evidence_map
            collected["current_field"] = "evidence_email_call"
            response_text = "Do you have any email communications or call recordings?"
        elif current_field == "evidence_email_call":
            if any(kw in lower_msg for kw in ["yes", "yeah", "ha", "అవును", "हाँ"]):
                evidence_map["Audio"] = True
            collected["evidence_map"] = evidence_map
            
            # Evidence collection complete! Generate Narrative, Timeline & Admin Notes
            # Move to step 6
            collected["step"] = 6
            collected["current_field"] = "submit_confirmation"

            # 1. Timeline assembly
            inc_date = collected.get("transaction_date") or collected.get("last_access") or "Incident Date"
            inc_time = collected.get("transaction_time") or "Incident Time"
            platform = collected.get("platform") or "Platform"
            amount = collected.get("amount") or "Amount lost"
            bank = collected.get("bank_name") or "Bank name"

            timeline_str = (
                f"- {inc_date} {inc_time}: Victim initially contacted through {platform}.\n"
                f"- {inc_date}: Suspect social-engineered victim into clicking file / card transfer.\n"
                f"- {inc_date}: Unauthorized withdrawal of ₹{amount} from {bank}."
            )
            collected["timeline"] = timeline_str

            # 2. NCRP Narrative Generation
            narrative = (
                f"On {inc_date}, the victim received a suspicious communication through {platform} from an unknown individual. "
                f"The suspect persuaded the victim to perform a transaction or open a file. Following the interaction, "
                f"unauthorized financial transactions occurred from the victim's {bank} account, resulting in a loss of ₹{amount}. "
                f"The victim believes the incident is associated with {detected_sub} and online financial fraud."
            )
            collected["fraud_description"] = narrative

            # 3. Hidden Admin Notes
            trace = "Low"
            if collected.get("suspect_upi") and collected["suspect_upi"] != "UNKNOWN": trace = "High"
            elif collected.get("suspect_mobile") and collected["suspect_mobile"] != "UNKNOWN": trace = "Medium"

            risk_val = "Low"
            if detected_cat == "Women and Children Related Crime" or detected_sub == "Blackmail / Sextortion" or escalate:
                risk_val = "Critical"
            elif amount and str(amount).isdigit() and int(amount) >= 500000:
                risk_val = "Critical"
            elif amount and str(amount).isdigit() and int(amount) >= 100000:
                risk_val = "High"
            elif amount and str(amount).isdigit() and int(amount) >= 1000:
                risk_val = "Medium"

            admin_notes = (
                f"\n\n--- [ADMIN_INVESTIGATION_NOTES] ---\n"
                f"Potential Crime: {detected_sub}\n"
                f"Risk Level: {risk_val}\n"
                f"Amount Lost: ₹{amount}\n"
                f"Suspect Traceability: {trace}\n"
                f"Investigation Priority: {'High' if risk_val in ['High', 'Critical'] else 'Medium'}\n"
                f"Escalated to 1930: {'Yes' if escalate else 'No'}\n"
            )
            collected["fraud_description"] += admin_notes
            collected["risk_level"] = risk_val

            response_text = (
                f"I have compiled your details and generated a professional NCRP narrative for investigation.\n\n"
                f"Navigating to Review & Submit page. Here is the draft summary:\n"
                f"  - Crime Type: {detected_sub}\n"
                f"  - Amount lost: ₹{amount}\n"
                f"  - Risk Assessment: {risk_val}\n\n"
                f"Would you like to modify any information before proceeding to submission? (Yes/No)"
            )

    # -----------------------------------------------------------------------
    # Step 6: Review & Submit Confirmation
    # -----------------------------------------------------------------------
    elif step == 6:
        # Confirming submission
        if any(kw in lower_msg for kw in ["no", "incorrect", "wrong"]):
            response_text = "Understood. Please type which step you would like to edit (e.g. Victim Details, Incident Details) so we can modify the fields."
        else:
            is_complete = True
            response_text = "Excellent. All sections are complete. Please click the 'Confirm & Submit Report' button on the page to register the complaint."

    # -----------------------------------------------------------------------
    # Emergency Escalation Prepend
    # -----------------------------------------------------------------------
    if escalate:
        response_text = "⚠️ This is a high-priority cybercrime. Please also contact the 1930 Cybercrime Helpline immediately.\n\n" + response_text

    # Calculate Completeness scores
    cat_comp = 100 if session.detected_subcategory_id else 0
    
    # Victim completeness
    if collected.get("is_anonymous"):
        vic_comp = 100
    else:
        vic_filled = sum(1 for vf in VICTIM_FIELDS if collected.get(vf["name"]))
        vic_comp = int((vic_filled / len(VICTIM_FIELDS)) * 100)
    
    # Incident completeness
    dyn_questions = collected.get("dynamic_questions", [])
    if dyn_questions:
        inc_filled = sum(1 for q in dyn_questions if collected.get(q))
        inc_comp = int((inc_filled / len(dyn_questions)) * 100)
    else:
        inc_comp = 0
        
    # Suspect completeness
    sus_filled = sum(1 for sf in SUSPECT_FIELDS if collected.get(sf["name"]))
    sus_comp = int((sus_filled / len(SUSPECT_FIELDS)) * 100)

    # Evidence completeness score (None = 20%, Screenshot = 50%, Screenshot + Statement = 80%, all = 100%)
    ev_map = collected.get("evidence_map", {})
    ev_comp = 20
    if ev_map.get("Screenshot"): ev_comp = 50
    if ev_map.get("Screenshot") and ev_map.get("Bank Statement"): ev_comp = 80
    if ev_map.get("Screenshot") and ev_map.get("Bank Statement") and ev_map.get("Audio"): ev_comp = 100

    # Overall weighted score
    overall = int((cat_comp * 0.1) + (vic_comp * 0.2) + (inc_comp * 0.3) + (sus_comp * 0.2) + (ev_comp * 0.2))

    progress_breakdown = {
        "category": cat_comp,
        "victim": vic_comp,
        "incident": inc_comp,
        "suspect": sus_comp,
        "evidence": ev_comp,
        "overall": overall
    }

    # Save to session
    collected["step"] = step
    collected["current_field"] = current_field
    collected["attempt_count"] = attempt_count
    session.collected_data = collected

    return {
        "response": response_text,
        "detected_category": detected_cat,
        "detected_subcategory": detected_sub,
        "quality_score": overall,
        "is_high_priority": overall >= 80 or escalate or (detected_cat == "Women and Children Related Crime"),
        "is_complete": is_complete,
        "step": step,
        "progress_breakdown": progress_breakdown,
        "duplicate_warning": duplicate_warning
    }


# Keep analyze_chat for compatibility (routes it through process_dialogue_turn structure)
async def analyze_chat(
    history: List[Dict[str, Any]],
    current_message: str,
    previously_collected: Dict[str, Any] = None,
    language: str = "en-IN"
) -> Dict[str, Any]:
    # Dummy session call for backward compatibility
    # Normally handled in the endpoint by process_dialogue_turn directly
    return {"response": "Processed", "missing_fields": []}
