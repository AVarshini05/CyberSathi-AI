import logging
import re
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import settings
from app.models.complaint import ComplaintCategory, ComplaintSubcategory

logger = logging.getLogger(__name__)

# Global in-memory caches
CATEGORIES_CACHE: List[Dict[str, Any]] = []
SUBCATEGORIES_CACHE: List[Dict[str, Any]] = []

# Path to local feedback file
FEEDBACK_FILE_PATH = os.path.join("logs", "ai_feedback.jsonl")


class GeminiClassificationResponse(BaseModel):
    detected_language: str
    translated_text: str
    category_name: str
    subcategory_name: str
    confidence: int
    keywords: List[str]
    explanation: str
    ambiguous: bool


def load_and_cache_schemas(db: Session) -> None:
    """Load categories and subcategories from database and cache them in-memory."""
    global CATEGORIES_CACHE, SUBCATEGORIES_CACHE
    try:
        categories = db.query(ComplaintCategory).all()
        CATEGORIES_CACHE.clear()
        SUBCATEGORIES_CACHE.clear()
        
        for cat in categories:
            CATEGORIES_CACHE.append({
                "id": cat.id,
                "name": cat.name,
                "code": cat.code,
                "description": cat.description
            })
            for sub in cat.subcategories:
                SUBCATEGORIES_CACHE.append({
                    "id": sub.id,
                    "category_id": cat.id,
                    "name": sub.name,
                    "description": sub.description,
                    "category_name": cat.name
                })
        
        logger.info(f"Successfully cached {len(CATEGORIES_CACHE)} categories and {len(SUBCATEGORIES_CACHE)} subcategories.")
    except Exception as e:
        logger.error(f"Failed to load and cache database schemas: {e}")


def classify_complaint(description: str, db: Session) -> Dict[str, Any]:
    """
    Classify user description using Gemini (with translation to English).
    Falls back to a local keyword-based regex classifier if Gemini fails.
    """
    global CATEGORIES_CACHE, SUBCATEGORIES_CACHE
    
    # Ensure cache is populated
    if not CATEGORIES_CACHE or not SUBCATEGORIES_CACHE:
        load_and_cache_schemas(db)
        
    description_clean = description.strip()
    
    # Check for empty description
    if not description_clean:
        return {
            "category_id": 0,
            "subcategory_id": 0,
            "category_name": "Unknown",
            "subcategory_name": "Unknown",
            "detected_language": "Local Classifier (Fallback)",
            "translated_text": "",
            "confidence": 0,
            "keywords": [],
            "explanation": "No text description provided. Unable to determine the category.",
            "ambiguous": True
        }
        
    # Check for too short/vague description
    if len(description_clean) < 10:
        return {
            "category_id": 0,
            "subcategory_id": 0,
            "category_name": "Unknown",
            "subcategory_name": "Unknown",
            "detected_language": "Local Classifier (Fallback)",
            "translated_text": description_clean,
            "confidence": 45,
            "keywords": [],
            "explanation": "Description is too short or vague to confidently classify. Please select manually.",
            "ambiguous": True
        }
        
    # 1. Attempt Gemini classification
    try:
        result = _classify_with_gemini(description_clean)
        if result:
            mapped = _map_names_to_ids(result)
            if mapped:
                return mapped
    except Exception as e:
        logger.warning(f"Gemini classification failed: {e}. Falling back to rule-based classifier.")
        
    # 2. Fallback to local rule-based classifier
    return _classify_rule_based(description_clean)


def _classify_with_gemini(description: str) -> Optional[Dict[str, Any]]:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
        
    client = genai.Client(api_key=api_key)
    
    # Build list of categories and subcategories for prompt
    schema_info = []
    for sub in SUBCATEGORIES_CACHE:
        schema_info.append(f"- Category: '{sub['category_name']}', Subcategory: '{sub['name']}' ({sub['description']})")
        
    schema_str = "\n".join(schema_info)
    
    prompt = f"""
You are a senior cybercrime complaint intake officer.
Analyze the complaint like a trained cybercrime investigator.
Determine:
1. Attack method
2. Victim impact
3. Fraud mechanism
4. Threat type
5. Category
6. Subcategory

Allowed Classifications:
{schema_str}

User Description to Analyze:
\"\"\"{description}\"\"\"

Instructions:
1. Detect the language of the description (e.g. English, Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali, Marathi, or Hinglish/Telugish mixed).
2. If the text is not in English, translate it to English. Store this in 'translated_text'. If it is in English, 'translated_text' should be the original description.
3. Classify the incident into exactly one Category and Subcategory from the allowed list. Select the closest match.
4. Set 'ambiguous' to true ONLY if the description is genuinely vague or ambiguous and does not contain enough information to classify (e.g. "something suspicious happened", "help me", "my internet is down"). If the description contains clear indicators of a cybercrime (e.g. net banking compromise, bank account hacked, fake profile, online threats, unauthorized transaction), set 'ambiguous' to false. Missing entities (like UPI, amount, platform, transaction ID) do NOT prevent classification.
5. Calculate a confidence score between 0 and 100 based on these calibration rules:
   - Very clear, unambiguous cybercrime complaint with specific details (e.g. hacked profile with password changed, phishing link credential theft, trace of exact amounts/IDs) -> 90% to 98% confidence.
   - Moderately clear complaint with some indicators but fewer specific details (e.g. generic financial loss online, net banking transfer, bank account compromise, vague account recovery issue) -> 60% to 80% confidence.
   - Highly ambiguous or vague complaint with little or no cybercrime-specific indicators -> below 50% confidence.
   - Never assign 85% confidence as a generic default. It must be evidence-based.
6. Extract key words or trigger words that led to this decision.
7. Provide a detailed, evidence-based explanation (not generic matched keywords) including:
   - Indicators detected
   - Attack method
   - Classification rationale
   Example explanation format: "Detected unauthorized social media account access and blackmail involving photo-leak threats. These indicators strongly align with Social Media Hacking and Cyber Blackmail."

Return your response in structured JSON matching the following schema. Do NOT wrap in markdown formatting other than raw JSON.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeminiClassificationResponse,
            temperature=0.0
        )
    )
    
    try:
        data = json.loads(response.text)
        return data
    except Exception as e:
        logger.error(f"Failed to parse Gemini JSON output: {e}. Raw response: {response.text}")
        return None


def _map_names_to_ids(gemini_res: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    category_name = gemini_res.get("category_name", "").strip().lower()
    subcategory_name = gemini_res.get("subcategory_name", "").strip().lower()
    
    # Try to find matching subcategory and category in cache
    matched_sub = None
    for sub in SUBCATEGORIES_CACHE:
        if sub["name"].strip().lower() == subcategory_name:
            matched_sub = sub
            break
            
    # Fallback to loose matching (if name contains)
    if not matched_sub:
        for sub in SUBCATEGORIES_CACHE:
            if sub["name"].strip().lower() in subcategory_name or subcategory_name in sub["name"].strip().lower():
                matched_sub = sub
                break
                
    if matched_sub:
        return {
            "category_id": matched_sub["category_id"],
            "subcategory_id": matched_sub["id"],
            "category_name": matched_sub["category_name"],
            "subcategory_name": matched_sub["name"],
            "detected_language": gemini_res.get("detected_language", "English"),
            "translated_text": gemini_res.get("translated_text", ""),
            "confidence": gemini_res.get("confidence", 0),
            "keywords": gemini_res.get("keywords", []),
            "explanation": gemini_res.get("explanation", ""),
            "ambiguous": gemini_res.get("ambiguous", False)
        }
        
    return None


def _classify_rule_based(description: str) -> Dict[str, Any]:
    text = description.lower()
    
    # Explicit high-confidence indicators (UPI, UTR, OTP, Instagram, WhatsApp, Facebook, Trading, Investment, etc.)
    explicit_patterns = [
        r"\bupi\b", r"\butr\b", r"\botp\b", r"\binstagram\b", r"\binsta\b", r"\bwhatsapp\b", 
        r"\bfacebook\b", r"\bfb\b", r"\btrading\b", r"\binvestment\b", r"\binvested\b", r"\binvest\b",
        r"\bgpay\b", r"\bphonepe\b", r"\bpaytm\b", r"\bvpa\b", r"\bqr code\b", r"\bqr scanner\b",
        r"\bloan app\b", r"\binstant loan\b", r"\bblackmail\b", r"\bsextortion\b", r"\bransomware\b",
        r"\bmalware\b", r"\bwannacry\b", r"\bbitcoin\b", r"\bethereum\b", r"\busdt\b", r"\bcrypto\b",
        r"\bcryptocurrency\b", r"\bcard cloning\b", r"\bcvv\b", r"\batm card\b", r"\bfake profile\b",
        r"\bfake account\b", r"\bimpersonat", r"\bchild abuse\b", r"\bcsam\b", r"\bhacked\b", r"\bhack\b",
        r"\bhacker\b", r"\bcyberstalk\b", r"\bstalking\b", r"\bstalker\b", r"\bharass",
        r"\bphishing\b", r"\bcredential\b", r"\bverify account\b", r"\bfake email\b", r"\bfake bank\b",
        r"\bbank account\b", r"\bnet banking\b", r"\bcredit card\b", r"\bdebit card\b", r"\btransferred\b",
        r"\btransfer\b", r"\bdebited\b", r"\bdisappeared\b", r"\bcompromised\b", r"\baccess to my\b",
        r"\bunauthorized\b", r"\bmorphed\b", r"\bmorph\b", r"\bexplicit\b", r"\bobscene\b", r"\blinkedin\b",
        r"\btelegram\b", r"\bwebsite\b", r"\bencrypted\b", r"\bdecryption\b", r"\bransom\b", r"\b\.locked\b",
        r"\bdecrypt\b", r"\battachment\b"
    ]
    
    has_explicit_match = False
    for pat in explicit_patterns:
        if re.search(pat, text):
            has_explicit_match = True
            break
            
    if not has_explicit_match:
        return {
            "category_id": 0,
            "subcategory_id": 0,
            "category_name": "Unknown",
            "subcategory_name": "Unknown",
            "detected_language": "Local Classifier (Fallback)",
            "translated_text": description,
            "confidence": 45,
            "keywords": [],
            "explanation": "Unable to confidently determine category. Please select manually.",
            "ambiguous": True
        }
        
    # Rules dictionary linking subcategory names to list of keyword patterns
    rules = {
        "UPI Fraud": ["upi", "gpay", "phonepe", "paytm", "utr", "qr code", "qr scanner", "vpa", "ybl"],
        "Internet Banking Fraud": ["net banking", "internet banking", "bank account", "fund transfer", "login password", "transaction reference", "banking portal", "transferred", "transfer", "debited", "disappeared", "compromised", "unauthorized", "apk", "apk file", "apk link", "electricity connection", "electricity bill", "unpaid bill", "disconnected", "disconnect", "bank balance", "cleared out", "lost network", "sim lost", "malicious app"],
        "Debit/Credit Card Fraud": ["debit card", "credit card", "atm card", "card cloning", "cvv", "card details", "card number"],
        "Investment/Trading Scam": ["investment", "trading", "stock market", "telegram group", "telegram channel", "double return", "profits", "crypto investment"],
        "Loan App Fraud": ["loan app", "instant loan", "repayment blackmail", "loan contact", "harassing contacts", "loan interest"],
        "Cryptocurrency Fraud": ["bitcoin", "ethereum", "usdt", "txid", "crypto wallet", "blockchain tx", "coin transfer"],
        "Social Media Hacking": ["instagram", "facebook", "twitter", "linkedin", "snapchat", "hack", "hacked", "recovery code", "profile locked", "unauthorized login", "otp request"],
        "Fake Profile / Impersonation": ["fake profile", "fake account", "impersonate", "impersonation", "photos uploaded", "fake id", "stolen photos"],
        "Email Hacking": ["email hack", "gmail", "outlook", "yahoo mail", "recovery email", "inbox accessed"],
        "Phishing": ["phishing", "fake link", "credentials stolen", "login page", "verify account", "bank link", "fake bank email", "credential theft", "stole my login", "clicked the link", "verify my account"],
        "Ransomware / Malware Attack": [
            "ransomware", "malware", "encrypted", "encryption", "files encrypted", "all files encrypted", 
            "decryption", "decryption key", "decrypt", "decryptor", "ransom", "locked", ".locked", 
            "system locked", "screen locked", "bitcoin", "btc", "crypto payment", "wallet address", 
            "malicious attachment", "infected attachment", "phishing attachment", "phishing email attachment", 
            "trojan"
        ],
        "Cyber Stalking / Online Harassment": ["stalking", "stalk", "harass", "harassment", "abusive messages", "constant calls", "monitoring me", "morphed", "morph", "morphed video", "morphed photo", "explicit video", "explicit photo", "telegram group", "telegram channel", "linkedin"],
        "Blackmail / Sextortion": ["blackmail", "sextortion", "private video", "threaten leak", "leak photos", "nude call", "screen recording threat"],
        "Child Exploitation / Obscene Content": ["child abuse", "csam", "obscene video", "minor exploitation"]
    }
    
    matched_subname = None
    matched_keywords = []
    matched_score = 0
    confidence = 0
    explanation = ""
    ambiguous = False
    
    # 1. Ransomware Priority Logic
    # Core ransomware indicators that guarantee Ransomware / Malware Attack classification
    core_ransomware_indicators = [
        "ransomware", "malware", "encrypted", "encryption", "files encrypted", "all files encrypted", 
        "decryption", "decryption key", "decrypt", "decryptor", "ransom", "locked", ".locked", 
        "system locked", "screen locked", "malicious attachment", "infected attachment", 
        "phishing attachment", "phishing email attachment", "trojan"
    ]
    ransomware_matched = [kw for kw in core_ransomware_indicators if kw in text]
    
    if len(ransomware_matched) >= 1: # threshold = 1
        matched_subname = "Ransomware / Malware Attack"
        # Gather all matching indicators, including bitcoin/btc/crypto/wallet
        all_ransomware_kws = core_ransomware_indicators + ["bitcoin", "btc", "crypto payment", "wallet address"]
        matched_keywords = [kw for kw in all_ransomware_kws if kw in text]
        matched_score = len(matched_keywords) * 10
        explanation = f"Priority rule-based classification matched core Ransomware/Malware indicators: {', '.join(ransomware_matched)}."
        confidence = 90
    else:
        # 2. Weighted Scoring Loop
        for subname, keywords in rules.items():
            found = []
            for kw in keywords:
                if kw in text:
                    found.append(kw)
            
            # Determine weight based on category type
            if subname == "Ransomware / Malware Attack":
                weight = 10
            elif subname in ["UPI Fraud", "Internet Banking Fraud", "Debit/Credit Card Fraud", "Investment/Trading Scam", "Loan App Fraud", "Cryptocurrency Fraud"]:
                weight = 2
            else:
                weight = 1  # Default weight for other categories (Social Media, Cyber Stalking, Blackmail etc.)
                
            score = sum(len(kw) for kw in found) * weight
            if score > matched_score:
                matched_score = score
                matched_keywords = found
                matched_subname = subname
                
        if matched_subname:
            explanation = f"Local rule-based classification matched keywords to '{matched_subname}' with score {matched_score}."
            confidence = 85
            
    if matched_subname:
        pass
    else:
        # Check parent categories keywords if no subcategory matched
        if any(w in text for w in ["phishing", "credential", "verify account", "fake email", "fake bank", "stolen credentials"]):
            matched_subname = "Phishing"
            matched_keywords = [w for w in ["phishing", "credential", "verify account", "fake email", "fake bank", "stolen credentials"] if w in text]
            explanation = "Local fallback matched phishing/credential theft keywords to 'Phishing'."
            confidence = 80
        elif any(w in text for w in ["hacked", "hack", "account", "login", "password"]):
            matched_subname = "Social Media Hacking"
            matched_keywords = [w for w in ["hacked", "hack", "account", "login", "password"] if w in text]
            explanation = "Local fallback matched parent account recovery keywords to 'Social Media Hacking'."
            confidence = 80
        elif any(w in text for w in ["rupees", "rs", "money", "lost", "fraud", "scam", "cash"]):
            matched_subname = "UPI Fraud"
            matched_keywords = [w for w in ["rupees", "rs", "money", "lost", "fraud", "scam", "cash"] if w in text]
            explanation = "Local fallback matched financial loss keywords to 'UPI Fraud'."
            confidence = 80
        elif any(w in text for w in ["threat", "photo", "video", "blackmail", "leak"]):
            matched_subname = "Blackmail / Sextortion"
            matched_keywords = [w for w in ["threat", "photo", "video", "blackmail", "leak"] if w in text]
            explanation = "Local fallback matched blackmail threat keywords to 'Blackmail / Sextortion'."
            confidence = 80
        else:
            # Low confidence fallback - no category matched
            return {
                "category_id": 0,
                "subcategory_id": 0,
                "category_name": "Unknown",
                "subcategory_name": "Unknown",
                "detected_language": "Local Classifier (Fallback)",
                "translated_text": description,
                "confidence": 45,
                "keywords": [],
                "explanation": "Unable to confidently determine category. Please select manually.",
                "ambiguous": True
            }
        
    # Map subcategory name to cache IDs
    matched_sub = None
    for sub in SUBCATEGORIES_CACHE:
        if sub["name"] == matched_subname:
            matched_sub = sub
            break
            
    if not matched_sub:
        return {
            "category_id": 0,
            "subcategory_id": 0,
            "category_name": "Unknown",
            "subcategory_name": "Unknown",
            "detected_language": "Local Classifier (Fallback)",
            "translated_text": description,
            "confidence": 45,
            "keywords": [],
            "explanation": "Unable to confidently determine category. Please select manually.",
            "ambiguous": True
        }
        
    return {
        "category_id": matched_sub["category_id"],
        "subcategory_id": matched_sub["id"],
        "category_name": matched_sub["category_name"],
        "subcategory_name": matched_sub["name"],
        "detected_language": "Local Classifier (Fallback)",
        "translated_text": description,
        "confidence": confidence,
        "keywords": matched_keywords,
        "explanation": explanation,
        "ambiguous": ambiguous
    }


def log_classification_feedback(description: str, suggested_category_name: str, suggested_subcategory_name: str, action: str) -> None:
    """Log user feedback action (accepted, modified, ignored) to an anonymized jsonl file."""
    try:
        os.makedirs("logs", exist_ok=True)
        
        # Anonymize user description using SHA256 hash (PII protected)
        desc_hash = hashlib.sha256(description.encode('utf-8')).hexdigest()
        
        feedback_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "description_hash": desc_hash,
            "suggested_category": suggested_category_name,
            "suggested_subcategory": suggested_subcategory_name,
            "action": action
        }
        
        with open(FEEDBACK_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_data) + "\n")
            
        logger.info(f"AI classification feedback logged: {action}")
    except Exception as e:
        logger.error(f"Failed to log AI feedback: {e}")
