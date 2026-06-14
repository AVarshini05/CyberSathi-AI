import re
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


class ExtractedFieldDetail(BaseModel):
    value: Optional[str]
    confidence: int
    source: Optional[str]
    source_text: Optional[str]


class ExtractedBoolDetail(BaseModel):
    value: bool
    confidence: int
    source_text: Optional[str]


class VictimDetails(BaseModel):
    name: Optional[ExtractedFieldDetail]
    mobile: Optional[ExtractedFieldDetail]
    email: Optional[ExtractedFieldDetail]
    gender: Optional[ExtractedFieldDetail]
    state: Optional[ExtractedFieldDetail]
    city: Optional[ExtractedFieldDetail]
    social_media_id: Optional[ExtractedFieldDetail]


class SuspectDetails(BaseModel):
    name: Optional[ExtractedFieldDetail]
    mobile: Optional[ExtractedFieldDetail]
    upi: Optional[ExtractedFieldDetail]
    account_number: Optional[ExtractedFieldDetail]
    social_media_id: Optional[ExtractedFieldDetail]
    website_url: Optional[ExtractedFieldDetail]


class FinancialIdentifiers(BaseModel):
    upi_id: Optional[ExtractedFieldDetail]
    account_number: Optional[ExtractedFieldDetail]
    transaction_id: Optional[ExtractedFieldDetail]
    utr_number: Optional[ExtractedFieldDetail]
    reference_number: Optional[ExtractedFieldDetail]


class GeminiExtractionResponse(BaseModel):
    victim: Optional[VictimDetails]
    suspect: Optional[SuspectDetails]
    platform: Optional[ExtractedFieldDetail]
    amount_lost: Optional[ExtractedFieldDetail]
    bait_payment: Optional[ExtractedFieldDetail]
    amount_demanded: Optional[ExtractedFieldDetail]
    threats: List[str]
    evidence: List[str]
    financial_identifiers: Optional[FinancialIdentifiers]


def extract_entities(description: str) -> Dict[str, Any]:
    """
    Extract cybercrime incident entities from natural language description.
    Uses Gemini 2.5 Flash structured schema, falling back to local regex extraction if needed.
    """
    description_clean = description.strip()
    if not description_clean:
        return {
            "extracted_fields": {},
            "confidence_scores": {},
            "evidence_flags": {
                "screenshot_mentioned": False,
                "bank_receipt_mentioned": False,
                "chat_screenshot_mentioned": False,
                "video_mentioned": False,
                "audio_mentioned": False
            },
            "warnings": ["Empty description provided."]
        }

    # 1. Attempt Gemini structured extraction
    try:
        gemini_result = _extract_with_gemini(description_clean)
        if gemini_result:
            return run_post_extraction_validation(gemini_result, description_clean)
    except Exception as e:
        logger.warning(f"Gemini entity extraction failed: {e}. Falling back to regex backup extractor.")

    # 2. Fallback to Regex extraction
    fallback_result = _extract_fallback_regex(description_clean)
    return run_post_extraction_validation(fallback_result, description_clean)


def _extract_with_gemini(description: str) -> Optional[Dict[str, Any]]:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
You are a Senior Cyber Crime Investigation Officer.
Your task is NOT keyword extraction.
Your task is complaint understanding and evidence extraction.
Read the complaint like a real investigator.

INVESTIGATION PROCESS
Before extracting anything:
1. Identify Victim
2. Identify Suspect
3. Identify Scam Pattern
4. Identify Timeline
5. Identify Financial Loss
6. Identify Threats
7. Identify Platforms Used
8. Identify Evidence Mentioned

EXTRACTION RULES
- Extract ONLY information explicitly present in the description.
- Never guess. Never infer unsupported values. Never invent data.
- If a value is not explicitly present, return null for that field.
- For every extracted field, assign a confidence score as an integer between 0 and 100 (e.g. 90 to 100 for verified presence).

AMOUNT REASONING (Very Important)
Distinguish between:
- Amount Received (bait_payment)
- Amount Invested
- Amount Demanded
- Amount Paid
- Amount Lost (actual victim loss)
Example 1: "Received ₹150. Invested ₹120000. Blocked afterwards."
Result: bait_payment = 150, amount_lost = 120000.
Example 2: "Deposited ₹1,80,000. Profit grew to ₹12,00,000. They demanded 30% tax."
Result: amount_lost = 180000, amount_demanded = 360000. (Always calculate the absolute amount for percentage-based demands like 30% of 12,00,000).

VICTIM VS SUSPECT SEPARATION
Example: "I transferred money from my HDFC account to 9876543210."
Result: victim_bank = HDFC, suspect_account = 9876543210.
Never mix victim and suspect information.

PLATFORM DETECTION
Identify actual platform (WhatsApp, Telegram, Instagram, Facebook, Skype, Email, Phone Call, Website, Trading Portal). Return null if absent.

THREAT DETECTION
Detect contextual threats: Blackmail, Sextortion, Arrest Threat, Impersonation, Account Compromise, Credential Theft, Investment Manipulation, Task Fraud.

Analyze this description:
\"\"\"{description}\"\"\"

Return your response in structured JSON matching the schema. Do NOT wrap in markdown formatting other than raw JSON.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeminiExtractionResponse,
            temperature=0.0
        )
    )
    
    try:
        import json
        data = json.loads(response.text)
        
        extracted_fields = {}
        confidence_scores = {}
        
        def map_val(detail):
            if detail and isinstance(detail, dict) and detail.get("value") is not None:
                v = str(detail["value"])
                c = detail.get("confidence")
                # Handle float / probability confidence scores (0.0 to 1.0)
                try:
                    c_num = float(c) if c is not None else 85.0
                    if 0.0 < c_num <= 1.0:
                        c_num = c_num * 100
                    c = int(c_num)
                except ValueError:
                    c = 85
                
                s = str(detail.get("source_text") or detail.get("source") or v)
                return {
                    "value": v,
                    "source": s,
                    "source_text": s,
                    "status": "valid",
                    "confidence": c
                }
            return {
                "value": None,
                "source": None,
                "source_text": None,
                "status": "valid",
                "confidence": 0
            }
            
        # Extract victim details
        victim = data.get("victim") or {}
        extracted_fields["victim_name"] = map_val(victim.get("name"))
        extracted_fields["victim_mobile"] = map_val(victim.get("mobile"))
        extracted_fields["victim_email"] = map_val(victim.get("email"))
        extracted_fields["victim_gender"] = map_val(victim.get("gender"))
        extracted_fields["victim_state"] = map_val(victim.get("state"))
        extracted_fields["victim_city"] = map_val(victim.get("city"))
        extracted_fields["account_id"] = map_val(victim.get("social_media_id"))
        
        # Extract suspect details
        suspect = data.get("suspect") or {}
        extracted_fields["suspect_name"] = map_val(suspect.get("name"))
        extracted_fields["suspect_mobile"] = map_val(suspect.get("mobile"))
        extracted_fields["suspect_upi"] = map_val(suspect.get("upi"))
        extracted_fields["suspect_account_number"] = map_val(suspect.get("account_number"))
        extracted_fields["suspect_social_media_id"] = map_val(suspect.get("social_media_id"))
        extracted_fields["website_url"] = map_val(suspect.get("website_url"))
        
        # Extract financial identifiers
        fin = data.get("financial_identifiers") or {}
        extracted_fields["upi_id"] = map_val(fin.get("upi_id"))
        extracted_fields["account_number"] = map_val(fin.get("account_number"))
        extracted_fields["transaction_id"] = map_val(fin.get("transaction_id"))
        extracted_fields["utr_number"] = map_val(fin.get("utr_number"))
        extracted_fields["reference_number"] = map_val(fin.get("reference_number"))
        
        # Extract other values
        extracted_fields["platform"] = map_val(data.get("platform"))
        extracted_fields["fraud_platform"] = map_val(data.get("platform"))
        extracted_fields["amount_lost"] = map_val(data.get("amount_lost"))
        extracted_fields["amount_demanded"] = map_val(data.get("amount_demanded"))
        
        extracted_fields["incident_date"] = {"value": None, "source": None, "source_text": None, "status": "valid", "confidence": 0}
        extracted_fields["incident_time"] = {"value": None, "source": None, "source_text": None, "status": "valid", "confidence": 0}
        extracted_fields["fraud_channel"] = {"value": None, "source": None, "source_text": None, "status": "valid", "confidence": 0}
        
        # Threats
        threats_list = data.get("threats") or []
        threats_lower = [t.lower() for t in threats_list if isinstance(t, str)]
        
        blackmail = "blackmail" in threats_lower or "sextortion" in threats_lower or "arrest threat" in threats_lower
        sextortion = "sextortion" in threats_lower
        impersonation = "impersonation" in threats_lower
        compromised = "account compromise" in threats_lower or "credential theft" in threats_lower
        
        bool_indicators = {
            "threat_detected": len(threats_lower) > 0,
            "account_compromised": compromised,
            "blackmail_indicator": blackmail,
            "sextortion_indicator": sextortion,
            "impersonation_indicator": impersonation
        }
        
        for k, v in bool_indicators.items():
            extracted_fields[k] = {
                "value": v,
                "source": "Yes" if v else "No",
                "source_text": "Yes" if v else "No",
                "status": "valid",
                "confidence": 85 if v else 0
            }
            
        if sextortion:
            extracted_fields["threat_type"] = {"value": "Sextortion", "source": "Sextortion", "source_text": "Sextortion", "status": "valid", "confidence": 85}
        elif blackmail:
            extracted_fields["threat_type"] = {"value": "Blackmail", "source": "Blackmail", "source_text": "Blackmail", "status": "valid", "confidence": 85}
        else:
            extracted_fields["threat_type"] = {"value": None, "source": None, "source_text": None, "status": "valid", "confidence": 0}
            
        # Evidence
        evidence_list = data.get("evidence") or []
        evidence_lower = [e.lower() for e in evidence_list if isinstance(e, str)]
        
        evidence_flags = {
            "screenshot_mentioned": "screenshot" in evidence_lower or "image" in evidence_lower or "photo" in evidence_lower,
            "bank_receipt_mentioned": "receipt" in evidence_lower or "bank slip" in evidence_lower or "statement" in evidence_lower,
            "chat_screenshot_mentioned": "chat" in evidence_lower or "message" in evidence_lower,
            "video_mentioned": "video" in evidence_lower or "clip" in evidence_lower,
            "audio_mentioned": "audio" in evidence_lower or "voice call" in evidence_lower
        }
        
        for k, v in extracted_fields.items():
            confidence_scores[k] = v.get("confidence", 0)
            
        return {
            "extracted_fields": extracted_fields,
            "confidence_scores": confidence_scores,
            "evidence_flags": evidence_flags,
            "warnings": []
        }
    except Exception as e:
        logger.error(f"Failed to parse Gemini extraction JSON: {e}. Raw response: {response.text}")
        return None


def classify_phone_number_context(number: str, description: str) -> str:
    """
    Classify a phone number as 'victim', 'suspect', or 'ambiguous' based on context keywords.
    """
    text = description.lower()
    escaped_num = re.escape(number)
    matches = list(re.finditer(escaped_num, text))
    if not matches:
        return 'ambiguous'
        
    victim_score = 0
    suspect_score = 0
    
    victim_kws = ["my", "i am", "victim", "contact me", "my phone", "my mobile", "my number", "contact number"]
    suspect_kws = ["fraudster", "scammer", "hacker", "suspect", "accused", "cheat", "scam", "called from", "got call", "he use", "she use", "demanded", "cheated", "whatsapp number", "fraudster mobile", "scammer mobile", "fraudster number", "scammer number", "accused number"]

    for m in matches:
        start_idx = max(0, m.start() - 50)
        end_idx = min(len(text), m.end() + 10)
        context = text[start_idx:end_idx]
        
        for kw in victim_kws:
            if kw in context:
                victim_score += 1
                
        for kw in suspect_kws:
            if kw in context:
                suspect_score += 1

    if suspect_score > victim_score:
        return 'suspect'
    elif victim_score > suspect_score:
        return 'victim'
    else:
        return 'ambiguous'


def _extract_fallback_regex(description: str) -> Dict[str, Any]:
    text = description.lower()
    extracted_fields = {}
    confidence_scores = {}
    warnings = []
    
    fields = [
        "victim_name", "victim_mobile", "victim_email", "victim_gender", "victim_state", "victim_city",
        "incident_date", "incident_time", "amount_lost", "amount_demanded", "fraud_platform", "platform", "account_id", "fraud_channel",
        "upi_id", "account_number", "transaction_id", "utr_number", "reference_number",
        "suspect_name", "suspect_mobile", "suspect_upi", "suspect_account_number", "suspect_social_media_id", "website_url",
        "claimed_identity", "crypto_wallet_address", "crypto_type"
    ]
    for f in fields:
        extracted_fields[f] = {"value": None, "source": None, "source_text": None, "status": "valid", "confidence": 0}
        confidence_scores[f] = 0
        
    evidence_flags = {
        "screenshot_mentioned": False,
        "bank_receipt_mentioned": False,
        "chat_screenshot_mentioned": False,
        "video_mentioned": False,
        "audio_mentioned": False
    }
    
    # 1. Mobile Numbers (Indian 10-digit)
    mobile_matches = re.findall(r"\b[6-9]\d{9}\b", description)
    mobiles = []
    for m in mobile_matches:
        if m not in mobiles:
            mobiles.append(m)
            
    if mobiles:
        classified_mobiles = []
        for m in mobiles:
            c_type = classify_phone_number_context(m, description)
            classified_mobiles.append((m, c_type))
            
        victims = [m for m, t in classified_mobiles if t == 'victim']
        suspects = [m for m, t in classified_mobiles if t == 'suspect']
        ambiguous = [m for m, t in classified_mobiles if t == 'ambiguous']
        
        if victims:
            extracted_fields["victim_mobile"] = {"value": victims[0], "source": victims[0], "source_text": victims[0], "status": "valid", "confidence": 90}
            confidence_scores["victim_mobile"] = 90
        if suspects:
            extracted_fields["suspect_mobile"] = {"value": suspects[0], "source": suspects[0], "source_text": suspects[0], "status": "valid", "confidence": 90}
            confidence_scores["suspect_mobile"] = 90
            
        # Fill unassigned slots with ambiguous numbers
        if not extracted_fields["victim_mobile"]["value"] and ambiguous:
            m = ambiguous.pop(0)
            has_suspect_kws = any(kw in text for kw in ["fraudster number", "scammer number", "hacker number", "suspect mobile", "accused number", "fraudster mobile", "scammer mobile"])
            if has_suspect_kws:
                extracted_fields["suspect_mobile"] = {"value": m, "source": m, "source_text": m, "status": "valid", "confidence": 85}
                confidence_scores["suspect_mobile"] = 85
            else:
                extracted_fields["victim_mobile"] = {"value": m, "source": m, "source_text": m, "status": "valid", "confidence": 85}
                confidence_scores["victim_mobile"] = 85
                
        if not extracted_fields["suspect_mobile"]["value"] and ambiguous:
            m = ambiguous.pop(0)
            extracted_fields["suspect_mobile"] = {"value": m, "source": m, "source_text": m, "status": "valid", "confidence": 85}
            confidence_scores["suspect_mobile"] = 85
            
    # 2. Emails
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", description)
    if emails:
        classified_emails = []
        for e in emails:
            escaped_val = re.escape(e)
            matches = list(re.finditer(escaped_val, text))
            e_type = 'ambiguous'
            if matches:
                victim_score = 0
                suspect_score = 0
                victim_kws = ["my email", "i am", "my address", "contact me at", "my gmail", "my mail"]
                suspect_kws = ["fraudster email", "scammer email", "hacker email", "suspect email", "received email from", "email claiming", "sent to email"]
                for m in matches:
                    start_idx = max(0, m.start() - 50)
                    end_idx = min(len(text), m.end() + 10)
                    context = text[start_idx:end_idx]
                    for kw in victim_kws:
                        if kw in context:
                            victim_score += 1
                    for kw in suspect_kws:
                        if kw in context:
                            suspect_score += 1
                if suspect_score > victim_score:
                    e_type = 'suspect'
                elif victim_score > suspect_score:
                    e_type = 'victim'
            classified_emails.append((e, e_type))
            
        victims = [e for e, t in classified_emails if t == 'victim']
        ambiguous = [e for e, t in classified_emails if t == 'ambiguous']
        
        if victims:
            extracted_fields["victim_email"] = {"value": victims[0], "source": victims[0], "source_text": victims[0], "status": "valid", "confidence": 90}
            confidence_scores["victim_email"] = 90
        elif ambiguous:
            # Only map to victim email if it doesn't look like a suspect email context
            e = ambiguous.pop(0)
            has_suspect_kws = any(kw in text for kw in ["fraudster email", "scammer email", "hacker email", "suspect email", "email claiming", "received from"])
            if not has_suspect_kws:
                extracted_fields["victim_email"] = {"value": e, "source": e, "source_text": e, "status": "valid", "confidence": 85}
                confidence_scores["victim_email"] = 85
        
    # 3. UPI IDs
    all_upi_ids = re.findall(r"\b[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\b", description)
    upi_ids = [u for u in all_upi_ids if u not in emails]
    if upi_ids:
        classified_upis = []
        for u in upi_ids:
            escaped_val = re.escape(u)
            matches = list(re.finditer(escaped_val, text))
            u_type = 'ambiguous'
            if matches:
                victim_score = 0
                suspect_score = 0
                victim_kws = ["my upi", "my side", "sender upi", "my account", "from my upi", "sent from my upi"]
                suspect_kws = ["sent to", "paid to", "transferred to", "beneficiary", "fraudster upi", "scammer upi", "cheat upi", "suspect upi", "receiver upi", "accused upi", "sent money to", "paid money to", "transferred money to", "send to", "pay to", "transfer to"]
                for m in matches:
                    start_idx = max(0, m.start() - 50)
                    end_idx = min(len(text), m.end() + 10)
                    context = text[start_idx:end_idx]
                    for kw in victim_kws:
                        if kw in context:
                            victim_score += 1
                    for kw in suspect_kws:
                        if kw in context:
                            suspect_score += 1
                if suspect_score > victim_score:
                    u_type = 'suspect'
                elif victim_score > suspect_score:
                    u_type = 'victim'
            classified_upis.append((u, u_type))
            
        victims = [u for u, t in classified_upis if t == 'victim']
        suspects = [u for u, t in classified_upis if t == 'suspect']
        ambiguous = [u for u, t in classified_upis if t == 'ambiguous']
        
        if victims:
            extracted_fields["upi_id"] = {"value": victims[0], "source": victims[0], "source_text": victims[0], "status": "valid", "confidence": 90}
            confidence_scores["upi_id"] = 90
        if suspects:
            extracted_fields["suspect_upi"] = {"value": suspects[0], "source": suspects[0], "source_text": suspects[0], "status": "valid", "confidence": 90}
            confidence_scores["suspect_upi"] = 90
            
        # fallback for ambiguous
        if not extracted_fields["upi_id"]["value"] and ambiguous:
            u = ambiguous.pop(0)
            has_suspect_kws = any(kw in text for kw in ["sent to", "paid to", "transferred to", "beneficiary", "fraudster", "scammer", "suspect"])
            if has_suspect_kws:
                extracted_fields["suspect_upi"] = {"value": u, "source": u, "source_text": u, "status": "valid", "confidence": 85}
                confidence_scores["suspect_upi"] = 85
            else:
                extracted_fields["upi_id"] = {"value": u, "source": u, "source_text": u, "status": "valid", "confidence": 85}
                confidence_scores["upi_id"] = 85
                
        if not extracted_fields["suspect_upi"]["value"] and ambiguous:
            u = ambiguous.pop(0)
            extracted_fields["suspect_upi"] = {"value": u, "source": u, "source_text": u, "status": "valid", "confidence": 85}
            confidence_scores["suspect_upi"] = 85
            
    # 4. Bank Account Numbers
    acc_matches = re.findall(r"\b\d{9,18}\b", description)
    accs = [a for a in acc_matches if a not in mobiles]
    if accs:
        classified_accs = []
        for a in accs:
            escaped_val = re.escape(a)
            matches = list(re.finditer(escaped_val, text))
            a_type = 'ambiguous'
            if matches:
                victim_score = 0
                suspect_score = 0
                victim_kws = ["my account", "my bank account", "debited from", "my bank", "savings account", "from my account"]
                suspect_kws = ["sent to account", "transferred to account", "beneficiary account", "fraudster account", "scammer account", "suspect account", "accused account", "hacker account", "sent money to", "transferred to", "paid to", "sent to", "send to", "transfer to", "pay to"]
                for m in matches:
                    start_idx = max(0, m.start() - 50)
                    end_idx = min(len(text), m.end() + 10)
                    context = text[start_idx:end_idx]
                    for kw in victim_kws:
                        if kw in context:
                            victim_score += 1
                    for kw in suspect_kws:
                        if kw in context:
                            suspect_score += 1
                if suspect_score > victim_score:
                    a_type = 'suspect'
                elif victim_score > suspect_score:
                    a_type = 'victim'
            classified_accs.append((a, a_type))
            
        victims = [a for a, t in classified_accs if t == 'victim']
        suspects = [a for a, t in classified_accs if t == 'suspect']
        ambiguous = [a for a, t in classified_accs if t == 'ambiguous']
        
        if victims:
            extracted_fields["account_number"] = {"value": victims[0], "source": victims[0], "source_text": victims[0], "status": "valid", "confidence": 90}
            confidence_scores["account_number"] = 90
        if suspects:
            extracted_fields["suspect_account_number"] = {"value": suspects[0], "source": suspects[0], "source_text": suspects[0], "status": "valid", "confidence": 90}
            confidence_scores["suspect_account_number"] = 90
            
        # fallback for ambiguous
        if not extracted_fields["account_number"]["value"] and ambiguous:
            a = ambiguous.pop(0)
            has_suspect_kws = any(kw in text for kw in ["sent to account", "transferred to account", "beneficiary account", "fraudster", "scammer"])
            if has_suspect_kws:
                extracted_fields["suspect_account_number"] = {"value": a, "source": a, "source_text": a, "status": "valid", "confidence": 85}
                confidence_scores["suspect_account_number"] = 85
            else:
                extracted_fields["account_number"] = {"value": a, "source": a, "source_text": a, "status": "valid", "confidence": 85}
                confidence_scores["account_number"] = 85
                
        if not extracted_fields["suspect_account_number"]["value"] and ambiguous:
            a = ambiguous.pop(0)
            extracted_fields["suspect_account_number"] = {"value": a, "source": a, "source_text": a, "status": "valid", "confidence": 85}
            confidence_scores["suspect_account_number"] = 85

    # 5. Transaction IDs / UTR Number (Must contain at least one digit to avoid matching pure-alphabetic words like "disconnected")
    potential_txs = re.findall(r"\b[A-Za-z0-9]{12,22}\b", description)
    txs = [t for t in potential_txs if not re.match(r"^\d{10}$", t) and any(c.isdigit() for c in t)]
    if txs:
        extracted_fields["transaction_id"] = {
            "value": txs[0],
            "source": txs[0],
            "source_text": txs[0],
            "status": "valid",
            "confidence": 85
        }
        confidence_scores["transaction_id"] = 85

    # 6. Cybercrime Indicators & Threat Detection
    account_comp_keywords = ["hacked", "hack", "compromised", "takeover", "hijacked", "access lost", "blocked me out"]
    blackmail_keywords = ["blackmail", "blackmailing", "threat", "threatening", "leak", "demand money", "extort"]
    # Sextortion explicitly requires intimate/sexual/nude keywords
    sextortion_keywords = ["sextortion", "nude", "naked", "intimate video", "leak nude", "intimate call", "nude call", "nude photo", "nude video", "private video", "leak private video"]
    impersonation_keywords = ["fake profile", "fake account", "impersonating", "impersonation", "using my name", "using my photo", "fake facebook", "fake instagram", "duplicate profile", "duplicate account", "impersonate"]
    
    account_compromised = any(w in text for w in account_comp_keywords)
    blackmail_indicator = any(w in text for w in blackmail_keywords)
    sextortion_indicator = any(w in text for w in sextortion_keywords)
    impersonation_indicator = any(w in text for w in impersonation_keywords)
    
    threat_detected = blackmail_indicator or sextortion_indicator or any(w in text for w in ["threat", "threaten"])
    
    threat_type_val = None
    if sextortion_indicator:
        threat_type_val = "Sextortion"
    elif any(w in text for w in ["leak my photo", "leak photo", "photos", "leak my photos", "leak photos"]):
        threat_type_val = "Photo Leak"
    elif any(w in text for w in ["leak my video", "leak video", "videos", "leak my videos", "leak videos"]):
        threat_type_val = "Video Leak"
    elif blackmail_indicator:
        threat_type_val = "Blackmail"
    elif account_compromised:
        threat_type_val = "Account Takeover Threat"
    elif threat_detected:
        threat_type_val = "Reputation Threat"

    indicators_map = {
        "account_compromised": account_compromised,
        "blackmail_indicator": blackmail_indicator,
        "sextortion_indicator": sextortion_indicator,
        "impersonation_indicator": impersonation_indicator,
        "threat_detected": threat_detected
    }
    for ind_key, ind_val in indicators_map.items():
        extracted_fields[ind_key] = {
            "value": ind_val,
            "source": "Yes" if ind_val else "No",
            "source_text": "Yes" if ind_val else "No",
            "status": "valid",
            "confidence": 85 if ind_val else 0
        }
        confidence_scores[ind_key] = 85 if ind_val else 0
        
    extracted_fields["threat_type"] = {
        "value": threat_type_val,
        "source": threat_type_val,
        "source_text": threat_type_val,
        "status": "valid",
        "confidence": 85 if threat_type_val else 0
    }
    confidence_scores["threat_type"] = 85 if threat_type_val else 0
        
    # 7. Amount Lost vs. Demanded context classification
    amount_matches = []
    # Pattern designed to extract numbers along with prefix/suffix currency indicators
    amount_pattern = (
        r"(?:lost|loss|losses|lose|losing|paid|pay|payment|payments|paying|sent|send|sending|transferred|transfer|transfers|transferring|debited|debit|debits|demand|demands|demanding|demanded|asking\s+for|ask\s+for|deposited|deposit|deposits|depositing|invested|invest|invests|investing|rs\.?|rupees|inr|₹)"
        r"\s*(?:of\s+|a\s+|an\s+|the\s+|payment\s+|payments\s+|sum\s+|amount\s+|charge\s+|charges\s+)*"
        r"\s*(?:rs\.?|rupees|inr|₹)?"
        r"\s*(\d+(?:,\d{2,3})*(?:\.\d+)?)"
        r"\s*(%|percent|bitcoin|btc|eth|usdt|dollars?|usd|\$|coins?)?"
    )
    
    cur_matches = re.finditer(amount_pattern, description, re.IGNORECASE)
    
    for m in cur_matches:
        val = m.group(1)
        clean_val = re.sub(r"[^\d.]", "", val)
        matched_str = m.group(0)
        
        # Determine currency
        currency = "INR"  # Default
        suffix = m.group(2)
        if suffix:
            currency = suffix
        else:
            matched_lower = matched_str.lower()
            if "₹" in matched_str:
                currency = "₹"
            elif "inr" in matched_lower:
                currency = "INR"
            elif "rs" in matched_lower:
                currency = "Rs"
            elif "rupees" in matched_lower:
                currency = "Rupees"
                
        start_idx = max(0, m.start() - 100)
        context = description[start_idx:m.end()].lower()
        
        is_demand = any(w in context for w in ["demand", "demanded", "demanding", "threat", "asking", "pay", "loan", "loans", "asking for", "request", "requested"])
        
        is_lost = any(w in context for w in ["lost", "paid", "transferred", "transfer", "debited", "loss", "deposited", "deposit", "invested", "invest"])
        if "sent" in context:
            # Check if any occurrence of "sent" is financial (doesn't refer to links, apks, or files)
            sent_positions = [i for i in range(len(context)) if context.startswith("sent", i)]
            has_financial_sent = False
            for pos in sent_positions:
                sent_context = context[pos:pos+50]
                is_non_financial = any(w in sent_context for w in ["link", "apk", "file", "message", "photo", "video", "otp", "code", "request", "sms", "text"])
                if not is_non_financial:
                    has_financial_sent = True
                    break
            if has_financial_sent:
                is_lost = True
                
        amount_matches.append((clean_val, currency, m.group(0), is_lost, is_demand))

    lost_vals = [(val, curr, src) for val, curr, src, l, d in amount_matches if l]
    demand_vals = [(val, curr, src) for val, curr, src, l, d in amount_matches if d]
    
    if not lost_vals and not demand_vals and amount_matches:
        if blackmail_indicator or sextortion_indicator or impersonation_indicator:
            demand_vals = [(amount_matches[0][0], amount_matches[0][1], amount_matches[0][2])]
        else:
            lost_vals = [(amount_matches[0][0], amount_matches[0][1], amount_matches[0][2])]
            
    if lost_vals:
        extracted_fields["amount_lost"] = {
            "value": lost_vals[0][0],
            "amount": lost_vals[0][0],
            "currency": lost_vals[0][1],
            "source": lost_vals[0][2],
            "source_text": lost_vals[0][2],
            "status": "valid",
            "confidence": 85
        }
        confidence_scores["amount_lost"] = 85
        
    if demand_vals:
        extracted_fields["amount_demanded"] = {
            "value": demand_vals[0][0],
            "amount": demand_vals[0][0],
            "currency": demand_vals[0][1],
            "source": demand_vals[0][2],
            "source_text": demand_vals[0][2],
            "status": "valid",
            "confidence": 85
        }
        confidence_scores["amount_demanded"] = 85

    # 8. Platform
    platforms = {
        "whatsapp": "WhatsApp",
        "instagram": "Instagram",
        "telegram": "Telegram",
        "facebook": "Facebook",
        "email": "Email",
        "phone call": "Phone Call",
        "upi": "UPI",
        "youtube": "YouTube",
        "linkedin": "LinkedIn",
        "twitter": "Twitter",
        "x": "X"
    }
    detected_platform = None
    for p, proper_name in platforms.items():
        if p in text:
            detected_platform = proper_name
            break
            
    if detected_platform:
        for p_key in ["platform", "fraud_platform"]:
            extracted_fields[p_key] = {
                "value": detected_platform,
                "source": detected_platform,
                "source_text": detected_platform,
                "status": "valid",
                "confidence": 85
            }
            confidence_scores[p_key] = 85

    # 9. Account ID extraction (like @xyz_official or account xyz_official)
    account_matches = re.findall(r"(?:account|profile|username|handle|id|user)\s+(?:name\s+)?(?:is\s+)?([a-zA-Z0-9._]+)", description, re.IGNORECASE)
    if not account_matches:
        account_matches = re.findall(r"\B@([a-zA-Z0-9._]+)", description)
        
    if account_matches:
        noise = ["my", "the", "a", "his", "her", "their", "is", "was", "active", "compromised", "hacked"]
        cleaned_accs = [acc for acc in account_matches if acc.lower() not in noise and len(acc) > 2]
        if cleaned_accs:
            extracted_fields["account_id"] = {
                "value": cleaned_accs[0],
                "source": cleaned_accs[0],
                "source_text": cleaned_accs[0],
                "status": "valid",
                "confidence": 85
            }
            confidence_scores["account_id"] = 85

    # 10. Evidence Flags
    if any(w in text for w in ["screenshot", "screen shot", "photo", "image", "pic"]):
        evidence_flags["screenshot_mentioned"] = True
    if any(w in text for w in ["receipt", "slip", "bank slip", "statement"]):
        evidence_flags["bank_receipt_mentioned"] = True
    if any(w in text for w in ["chat", "message", "whatsapp chat"]):
        evidence_flags["chat_screenshot_mentioned"] = True
    if any(w in text for w in ["video", "clip", "recording"]):
        evidence_flags["video_mentioned"] = True
    if any(w in text for w in ["audio", "voice note", "voice call"]):
        evidence_flags["audio_mentioned"] = True

    # 11. Cryptocurrency Wallet Address
    wallet_match = re.search(r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|0x[a-fA-F0-9]{40})\b", description)
    if wallet_match:
        extracted_fields["crypto_wallet_address"] = {
            "value": wallet_match.group(1),
            "source": wallet_match.group(0),
            "source_text": wallet_match.group(0),
            "status": "valid",
            "confidence": 85
        }
        confidence_scores["crypto_wallet_address"] = 85

    # Cryptocurrency Type
    crypto_type_val = None
    crypto_type_source = None
    if "bitcoin" in text or "btc" in text:
        crypto_type_val = "BTC"
        crypto_type_source = "Bitcoin" if "bitcoin" in text else "BTC"
    elif "ethereum" in text or "eth" in text:
        crypto_type_val = "ETH"
        crypto_type_source = "Ethereum" if "ethereum" in text else "ETH"
    elif "usdt" in text:
        crypto_type_val = "USDT"
        crypto_type_source = "USDT"
    elif "bnb" in text:
        crypto_type_val = "BNB"
        crypto_type_source = "BNB"
    elif "crypto" in text or "wallet" in text:
        crypto_type_val = "Other"
        crypto_type_source = "crypto"

    if crypto_type_val:
        extracted_fields["crypto_type"] = {
            "value": crypto_type_val,
            "source": crypto_type_source,
            "source_text": crypto_type_source,
            "status": "valid",
            "confidence": 85
        }
        confidence_scores["crypto_type"] = 85

    # 12. Victim Name & Claimed Identity
    claimed_match = re.search(
        r"\b(cbi\s+officer|police\s+officer|rbi\s+officer|ed\s+officer|customs\s+officer|cyber\s+crime\s+officer|fedex\s+executive|fedex\s+agent|narcotics\s+officer|narcotics\s+bureau\s+officer)\b",
        description,
        re.IGNORECASE
    )
    if claimed_match:
        claimed_val = claimed_match.group(1).title()
        extracted_fields["claimed_identity"] = {
            "value": claimed_val,
            "source": claimed_match.group(0),
            "source_text": claimed_match.group(0),
            "status": "valid",
            "confidence": 85
        }
        confidence_scores["claimed_identity"] = 85
        
    name_match = re.search(
        r"\b(?:my\s+name\s+is|i\s+am|this\s+is|myself)\s+([a-zA-Z]{3,20}(?:\s+[a-zA-Z]{3,20})?)\b",
        description,
        re.IGNORECASE
    )
    if name_match:
        name_val = name_match.group(1).strip()
        exclude_words = ["cbi", "police", "rbi", "ed", "customs", "cyber", "crime", "officer", "fedex", "narcotics", "bureau", "scammer", "hacker", "fraudster"]
        if not any(w in name_val.lower() for w in exclude_words):
            extracted_fields["victim_name"] = {
                "value": name_val,
                "source": name_match.group(0),
                "source_text": name_match.group(0),
                "status": "valid",
                "confidence": 85
            }
            confidence_scores["victim_name"] = 85
        
    return {
        "extracted_fields": extracted_fields,
        "confidence_scores": confidence_scores,
        "evidence_flags": evidence_flags,
        "warnings": warnings
    }


def run_post_extraction_validation(result: Dict[str, Any], description: str) -> Dict[str, Any]:
    extracted_fields = result.get("extracted_fields", {})
    confidence_scores = result.get("confidence_scores", {})
    warnings = result.get("warnings", [])
    
    text_lower = description.lower()
    
    # 1. Never Guess Values - verification of presence in description
    presence_fields = [
        "victim_mobile", "suspect_mobile", "upi_id", "suspect_upi", "transaction_id",
        "utr_number", "reference_number", "account_number", "suspect_account_number",
        "victim_email", "account_id", "suspect_social_media_id"
    ]
    
    for key in presence_fields:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip()
            clean_val = re.sub(r"[^\w]", "", val).lower()
            clean_desc = re.sub(r"[^\w]", "", description).lower()
            if clean_val and clean_val not in clean_desc:
                # Value was guessed/invented
                field["value"] = None
                field["source"] = None
                field["source_text"] = None
                field["confidence"] = 0
                confidence_scores[key] = 0
                
    # 2. Forbidden words rejection
    FORBIDDEN_WORDS = {
        "administrator", "provided", "using", "profile", "friend", "request", "message",
        "video", "call", "account", "user", "person", "someone", "group", "admin"
    }
    
    identifier_fields = [
        "transaction_id", "utr_number", "reference_number",
        "account_number", "suspect_account_number", "account_id",
        "victim_name", "suspect_name", "suspect_social_media_id",
        "upi_id", "suspect_upi"
    ]
    for key in identifier_fields:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip().lower()
            if val in FORBIDDEN_WORDS:
                field["value"] = None
                field["status"] = "needs_review"
                field["confidence"] = 0
                confidence_scores[key] = 0
                msg = f"Forbidden word '{val}' rejected for {key.replace('_', ' ').title()}."
                if msg not in warnings:
                    warnings.append(msg)

    # 3. Context-aware validation and separation for Mobiles
    victim_mobile_val = extracted_fields.get("victim_mobile", {}).get("value")
    if victim_mobile_val:
        c_type = classify_phone_number_context(victim_mobile_val, description)
        suspect_kws = ["fraudster number", "scammer number", "hacker number", "suspect mobile", "accused number", "fraudster mobile", "scammer mobile", "accused mobile", "accused number"]
        has_suspect_phrase = any(kw in text_lower for kw in suspect_kws)
        
        if c_type == 'suspect' or (has_suspect_phrase and c_type != 'victim'):
            suspect_mobile_val = extracted_fields.get("suspect_mobile", {}).get("value")
            if not suspect_mobile_val:
                extracted_fields["suspect_mobile"] = {
                    "value": victim_mobile_val,
                    "source": extracted_fields["victim_mobile"].get("source") or victim_mobile_val,
                    "source_text": extracted_fields["victim_mobile"].get("source_text") or victim_mobile_val,
                    "status": "valid",
                    "confidence": 90
                }
                confidence_scores["suspect_mobile"] = 90
                
            extracted_fields["victim_mobile"] = {
                "value": None,
                "source": None,
                "source_text": None,
                "status": "valid",
                "confidence": 0
            }
            confidence_scores["victim_mobile"] = 0
            warnings.append("Context indicates the extracted mobile number belongs to the suspect/fraudster. Reassigned to Suspect Mobile.")

    # 4. Context-aware separation for UPI IDs
    victim_upi_val = extracted_fields.get("upi_id", {}).get("value")
    if victim_upi_val:
        escaped_val = re.escape(victim_upi_val)
        matches = list(re.finditer(escaped_val, text_lower))
        u_type = 'ambiguous'
        if matches:
            victim_score = 0
            suspect_score = 0
            victim_kws = ["my upi", "my side", "sender upi", "my account", "from my upi", "sent from my upi"]
            suspect_kws = ["sent to", "paid to", "transferred to", "beneficiary", "fraudster upi", "scammer upi", "cheat upi", "suspect upi", "receiver upi", "accused upi", "sent money to", "paid money to", "transferred money to", "send to", "pay to", "transfer to"]
            for m in matches:
                start_idx = max(0, m.start() - 50)
                end_idx = min(len(text_lower), m.end() + 10)
                context = text_lower[start_idx:end_idx]
                for kw in victim_kws:
                    if kw in context:
                        victim_score += 1
                for kw in suspect_kws:
                    if kw in context:
                        suspect_score += 1
            if suspect_score > victim_score:
                u_type = 'suspect'
            elif victim_score > suspect_score:
                u_type = 'victim'
                
        if u_type == 'suspect':
            suspect_upi_val = extracted_fields.get("suspect_upi", {}).get("value")
            if not suspect_upi_val:
                extracted_fields["suspect_upi"] = {
                    "value": victim_upi_val,
                    "source": extracted_fields["upi_id"].get("source") or victim_upi_val,
                    "source_text": extracted_fields["upi_id"].get("source_text") or victim_upi_val,
                    "status": "valid",
                    "confidence": 90
                }
                confidence_scores["suspect_upi"] = 90
            extracted_fields["upi_id"] = {
                "value": None,
                "source": None,
                "source_text": None,
                "status": "valid",
                "confidence": 0
            }
            confidence_scores["upi_id"] = 0
            warnings.append("Context indicates the extracted UPI ID belongs to the suspect. Reassigned to Suspect UPI.")

    # 5. Context-aware separation for Account Numbers
    victim_acc_val = extracted_fields.get("account_number", {}).get("value")
    if victim_acc_val:
        escaped_val = re.escape(victim_acc_val)
        matches = list(re.finditer(escaped_val, text_lower))
        a_type = 'ambiguous'
        if matches:
            victim_score = 0
            suspect_score = 0
            victim_kws = ["my account", "my bank account", "debited from", "my bank", "savings account", "from my account"]
            suspect_kws = ["sent to account", "transferred to account", "beneficiary account", "fraudster account", "scammer account", "suspect account", "accused account", "hacker account", "sent money to", "transferred to", "paid to", "sent to", "send to", "transfer to", "pay to"]
            for m in matches:
                start_idx = max(0, m.start() - 50)
                end_idx = min(len(text_lower), m.end() + 10)
                context = text_lower[start_idx:end_idx]
                for kw in victim_kws:
                    if kw in context:
                        victim_score += 1
                for kw in suspect_kws:
                    if kw in context:
                        suspect_score += 1
            if suspect_score > victim_score:
                a_type = 'suspect'
            elif victim_score > suspect_score:
                a_type = 'victim'
                
        if a_type == 'suspect':
            suspect_acc_val = extracted_fields.get("suspect_account_number", {}).get("value")
            if not suspect_acc_val:
                extracted_fields["suspect_account_number"] = {
                    "value": victim_acc_val,
                    "source": extracted_fields["account_number"].get("source") or victim_acc_val,
                    "source_text": extracted_fields["account_number"].get("source_text") or victim_acc_val,
                    "status": "valid",
                    "confidence": 90
                }
                confidence_scores["suspect_account_number"] = 90
            extracted_fields["account_number"] = {
                "value": None,
                "source": None,
                "source_text": None,
                "status": "valid",
                "confidence": 0
            }
            confidence_scores["account_number"] = 0
            warnings.append("Context indicates the bank account number belongs to the suspect. Reassigned to Suspect Account Number.")

    # 6. Sextortion vs Blackmail Logic validation
    sextortion_field = extracted_fields.get("sextortion_indicator")
    if sextortion_field and sextortion_field.get("value") is True:
        intimate_keywords = ["nude", "naked", "intimate", "private video", "sexual", "sextortion", "video call recording", "recording of me"]
        has_intimate = any(w in text_lower for w in intimate_keywords)
        if not has_intimate:
            # Downgrade to blackmail
            extracted_fields["sextortion_indicator"] = {
                "value": False,
                "source": "No",
                "source_text": "No",
                "status": "valid",
                "confidence": 0
            }
            confidence_scores["sextortion_indicator"] = 0
            
            extracted_fields["blackmail_indicator"] = {
                "value": True,
                "source": "Yes",
                "source_text": "Yes",
                "status": "valid",
                "confidence": 90
            }
            confidence_scores["blackmail_indicator"] = 90
            
            threat_type_field = extracted_fields.get("threat_type")
            if threat_type_field and threat_type_field.get("value") == "Sextortion":
                if "photo" in text_lower or "pic" in text_lower:
                    threat_type_field["value"] = "Photo Leak"
                elif "video" in text_lower:
                    threat_type_field["value"] = "Video Leak"
                else:
                    threat_type_field["value"] = "Blackmail"

    # 7. Ambiguous context checks for mobiles
    for key in ["victim_mobile", "suspect_mobile"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"])
            c_type = classify_phone_number_context(val, description)
            if c_type == 'ambiguous':
                field["status"] = "needs_review"
                field["confidence"] = 50
                confidence_scores[key] = 50
                msg = f"Mobile number context for {key.replace('_', ' ').title()} is ambiguous. Marked for review."
                if msg not in warnings:
                    warnings.append(msg)

    # 8. Mobile fields validation format
    for key in ["victim_mobile", "suspect_mobile"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip()
            cleaned = re.sub(r"\D", "", val)
            if len(cleaned) == 12 and cleaned.startswith("91"):
                cleaned = cleaned[2:]
            elif len(cleaned) == 11 and cleaned.startswith("0"):
                cleaned = cleaned[1:]
                
            if len(cleaned) != 10 or any(c.isalpha() for c in val):
                field["value"] = None
                field["status"] = "needs_review"
                field["confidence"] = 0
                confidence_scores[key] = 0
                msg = f"Invalid {key.replace('_', ' ').title()} '{val}': Must contain valid digits."
                if msg not in warnings:
                    warnings.append(msg)
            else:
                field["value"] = cleaned
                
    # 9. Email fields validation
    for key in ["victim_email"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip()
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_regex, val):
                field["value"] = None
                field["status"] = "needs_review"
                field["confidence"] = 0
                confidence_scores[key] = 0
                msg = f"Invalid Victim Email '{val}': Must match email pattern."
                if msg not in warnings:
                    warnings.append(msg)
                
    # 10. UPI fields validation
    for key in ["upi_id", "suspect_upi"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip()
            if "@" not in val:
                field["value"] = None
                field["status"] = "needs_review"
                field["confidence"] = 0
                confidence_scores[key] = 0
                msg = f"Invalid {key.replace('_', ' ').title()} '{val}': Must contain '@'."
                if msg not in warnings:
                    warnings.append(msg)
                
    # 11. Transaction ID, UTR Number, Reference Number validation
    for key in ["transaction_id", "utr_number", "reference_number"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip()
            if not any(c.isdigit() for c in val):
                field["value"] = None
                field["status"] = "needs_review"
                field["confidence"] = 0
                confidence_scores[key] = 0
                msg = f"Invalid {key.replace('_', ' ').title()} '{val}': Must contain numbers."
                if msg not in warnings:
                    warnings.append(msg)

    # 12. Username / Name validation (victim_name, suspect_name, account_id, suspect_social_media_id)
    COMMON_ENGLISH_WORDS = {
        "the", "and", "for", "you", "that", "this", "with", "have", "not", "but", "his", "her",
        "him", "she", "they", "them", "was", "were", "been", "has", "had", "are", "our", "your",
        "someone", "somebody", "nobody", "anybody", "people", "person", "friend", "profile",
        "account", "user", "username", "admin", "administrator", "using", "provided", "request",
        "message", "video", "call", "group", "hacker", "scammer", "fraudster", "victim", "suspect"
    }
    for key in ["victim_name", "suspect_name", "account_id", "suspect_social_media_id"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip()
            if len(val) < 3 or val.lower() in COMMON_ENGLISH_WORDS or val.lower() in FORBIDDEN_WORDS:
                field["value"] = None
                field["status"] = "needs_review"
                field["confidence"] = 0
                confidence_scores[key] = 0
                msg = f"Invalid {key.replace('_', ' ').title()} '{val}': Username must be at least 3 characters and not a common word."
                if msg not in warnings:
                    warnings.append(msg)

    # 13. Amount validations
    for key in ["amount_lost", "amount_demanded", "bait_payment"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip()
            
            # If the value is a percentage (e.g. 30) or the source text mentions percentage
            source_txt = str(field.get("source_text") or field.get("source") or "").lower()
            if "%" in source_txt or "percent" in source_txt or val.endswith("%") or "percent" in val.lower():
                try:
                    pct_val = re.sub(r"[^\d.]", "", val)
                    pct = float(pct_val)
                    if pct <= 100:  # Only calculate if the percentage value is <= 100 (prevents double calculation)
                        # Search for large numbers in description
                        all_nums = [float(re.sub(r"[^\d.]", "", n)) for n in re.findall(r"\b\d+(?:,\d{2,3})*(?:\.\d+)?\b", description)]
                        large_nums = [n for n in all_nums if n > 100 and n != pct]
                        if large_nums:
                            base_val = max(large_nums)
                            calculated = (pct / 100.0) * base_val
                            if calculated.is_integer():
                                val = str(int(calculated))
                            else:
                                val = f"{calculated:.2f}"
                except ValueError:
                    pass
            
            # If it contains range words or multiple numbers, extract the first valid number group
            num_matches = re.findall(r"\d+(?:,\d{2,3})*(?:\.\d+)?", val)
            cleaned = None
            if num_matches:
                cleaned = re.sub(r"[^\d.]", "", num_matches[0])
            
            is_valid = False
            if cleaned:
                try:
                    float(cleaned)
                    is_valid = True
                except ValueError:
                    pass
            if not is_valid:
                field["value"] = None
                if "amount" in field:
                    field["amount"] = None
                if "currency" in field:
                    field["currency"] = None
                field["status"] = "needs_review"
                field["confidence"] = 0
                confidence_scores[key] = 0
                msg = f"Invalid {key.replace('_', ' ').title()} '{val}': Must be numeric."
                if msg not in warnings:
                    warnings.append(msg)
            else:
                field["value"] = cleaned
                if "amount" in field:
                    field["amount"] = cleaned
            
    # 14. Ensure extra fields (crypto_wallet_address, claimed_identity, crypto_type) are populated
    # (especially if the initial extraction was Gemini-based and lacked these keys)
    if not extracted_fields.get("crypto_wallet_address") or not extracted_fields["crypto_wallet_address"].get("value"):
        wallet_match = re.search(r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|0x[a-fA-F0-9]{40})\b", description)
        if wallet_match:
            extracted_fields["crypto_wallet_address"] = {
                "value": wallet_match.group(1),
                "source": wallet_match.group(0),
                "source_text": wallet_match.group(0),
                "status": "valid",
                "confidence": 85
            }
            confidence_scores["crypto_wallet_address"] = 85
        else:
            extracted_fields["crypto_wallet_address"] = {"value": None, "source": None, "source_text": None, "status": "valid", "confidence": 0}
            confidence_scores["crypto_wallet_address"] = 0

    if not extracted_fields.get("claimed_identity") or not extracted_fields["claimed_identity"].get("value"):
        claimed_match = re.search(
            r"\b(cbi\s+officer|police\s+officer|rbi\s+officer|ed\s+officer|customs\s+officer|cyber\s+crime\s+officer|fedex\s+executive|fedex\s+agent|narcotics\s+officer|narcotics\s+bureau\s+officer)\b",
            description,
            re.IGNORECASE
        )
        if claimed_match:
            claimed_val = claimed_match.group(1).title()
            extracted_fields["claimed_identity"] = {
                "value": claimed_val,
                "source": claimed_match.group(0),
                "source_text": claimed_match.group(0),
                "status": "valid",
                "confidence": 85
            }
            confidence_scores["claimed_identity"] = 85
        else:
            extracted_fields["claimed_identity"] = {"value": None, "source": None, "source_text": None, "status": "valid", "confidence": 0}
            confidence_scores["claimed_identity"] = 0

    if not extracted_fields.get("crypto_type") or not extracted_fields["crypto_type"].get("value"):
        crypto_type_val = None
        crypto_type_source = None
        if "bitcoin" in text_lower or "btc" in text_lower:
            crypto_type_val = "BTC"
            crypto_type_source = "Bitcoin" if "bitcoin" in text_lower else "BTC"
        elif "ethereum" in text_lower or "eth" in text_lower:
            crypto_type_val = "ETH"
            crypto_type_source = "Ethereum" if "ethereum" in text_lower else "ETH"
        elif "usdt" in text_lower:
            crypto_type_val = "USDT"
            crypto_type_source = "USDT"
        elif "bnb" in text_lower:
            crypto_type_val = "BNB"
            crypto_type_source = "BNB"
        elif "crypto" in text_lower or "wallet" in text_lower:
            crypto_type_val = "Other"
            crypto_type_source = "crypto"

        if crypto_type_val:
            extracted_fields["crypto_type"] = {
                "value": crypto_type_val,
                "source": crypto_type_source,
                "source_text": crypto_type_source,
                "status": "valid",
                "confidence": 85
            }
            confidence_scores["crypto_type"] = 85
        else:
            extracted_fields["crypto_type"] = {"value": None, "source": None, "source_text": None, "status": "valid", "confidence": 0}
            confidence_scores["crypto_type"] = 0

    result["extracted_fields"] = extracted_fields
    result["confidence_scores"] = confidence_scores
    result["warnings"] = warnings
    return result
