import re
import logging
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Schema Models (for Gemini structured output)
# ---------------------------------------------------------------------------

class ExtractedFieldDetail(BaseModel):
    value: Optional[str] = None
    confidence: int = 0
    source: Optional[str] = None
    source_text: Optional[str] = None


class ExtractedBoolDetail(BaseModel):
    value: bool = False
    confidence: int = 0
    source_text: Optional[str] = None


class VictimDetails(BaseModel):
    name: Optional[ExtractedFieldDetail] = None
    mobile: Optional[ExtractedFieldDetail] = None
    email: Optional[ExtractedFieldDetail] = None
    gender: Optional[ExtractedFieldDetail] = None
    state: Optional[ExtractedFieldDetail] = None
    city: Optional[ExtractedFieldDetail] = None
    social_media_id: Optional[ExtractedFieldDetail] = None


class SuspectDetails(BaseModel):
    name: Optional[ExtractedFieldDetail] = None
    mobile: Optional[ExtractedFieldDetail] = None
    upi: Optional[ExtractedFieldDetail] = None
    account_number: Optional[ExtractedFieldDetail] = None
    social_media_id: Optional[ExtractedFieldDetail] = None
    website_url: Optional[ExtractedFieldDetail] = None


class FinancialIdentifiers(BaseModel):
    upi_id: Optional[ExtractedFieldDetail] = None
    account_number: Optional[ExtractedFieldDetail] = None
    transaction_id: Optional[ExtractedFieldDetail] = None
    utr_number: Optional[ExtractedFieldDetail] = None
    reference_number: Optional[ExtractedFieldDetail] = None


class PhishingEvidence(BaseModel):
    """Fields specific to phishing, BEC, and email-based fraud."""
    sender_email: Optional[ExtractedFieldDetail] = None
    recipient_email: Optional[ExtractedFieldDetail] = None
    suspicious_domain: Optional[ExtractedFieldDetail] = None
    phishing_url: Optional[ExtractedFieldDetail] = None
    attachment_name: Optional[ExtractedFieldDetail] = None
    attachment_type: Optional[ExtractedFieldDetail] = None
    impersonated_org: Optional[ExtractedFieldDetail] = None


class GeminiExtractionResponse(BaseModel):
    victim: Optional[VictimDetails] = None
    suspect: Optional[SuspectDetails] = None
    platform: Optional[ExtractedFieldDetail] = None
    amount_lost: Optional[ExtractedFieldDetail] = None
    bait_payment: Optional[ExtractedFieldDetail] = None
    amount_demanded: Optional[ExtractedFieldDetail] = None
    threats: List[str] = []
    evidence: List[str] = []
    financial_identifiers: Optional[FinancialIdentifiers] = None
    # --- Extended fields ---
    phishing: Optional[PhishingEvidence] = None
    incident_date: Optional[ExtractedFieldDetail] = None
    incident_time: Optional[ExtractedFieldDetail] = None
    claimed_identity: Optional[ExtractedFieldDetail] = None
    crypto_type: Optional[ExtractedFieldDetail] = None
    crypto_wallet_address: Optional[ExtractedFieldDetail] = None
    attack_method: Optional[ExtractedFieldDetail] = None
    scam_pattern: Optional[ExtractedFieldDetail] = None
    digital_arrest: Optional[ExtractedFieldDetail] = None
    ransomware_name: Optional[ExtractedFieldDetail] = None
    os_affected: Optional[ExtractedFieldDetail] = None
    cloned_voice: Optional[ExtractedFieldDetail] = None
    cloned_video: Optional[ExtractedFieldDetail] = None
    biometric_manipulation: Optional[ExtractedFieldDetail] = None


# ---------------------------------------------------------------------------
# Master field list (drives normalisation + frontend display)
# ---------------------------------------------------------------------------

ALL_EXTRACTION_FIELDS = [
    # Victim
    "victim_name", "victim_phone", "victim_mobile", "victim_email",
    "victim_address", "victim_city", "victim_state", "victim_gender",
    # Suspect contact / identity
    "suspect_name", "suspect_phone_numbers", "suspect_mobile",
    "suspect_emails", "suspect_social_media_handles", "suspect_social_media_id",
    "suspect_usernames", "suspect_bank_accounts", "suspect_account_number",
    "suspect_ifsc_codes", "suspect_upi_ids", "suspect_upi",
    "suspect_wallet_addresses", "crypto_wallet_address",
    "suspect_websites", "website_url", "suspect_urls",
    # Identity / impersonation
    "claimed_identity", "impersonated_identity",
    # Incident context
    "incident_date", "incident_time", "incident_location", "incident_duration",
    # Platform
    "platforms_used", "platform", "fraud_platform", "fraud_channel",
    # Financial
    "amount_lost", "amount_demanded", "currency", "payment_method",
    "transaction_id", "reference_number", "bank_name", "account_number",
    "ifsc_code", "branch_name", "beneficiary_name", "upi_id", "upi_app",
    "last_4_digits", "card_type", "cryptocurrency_name", "cryptocurrency_amount",
    # Device / network
    "ip_address", "domain_name", "apk_name", "executable_name", "malware_file_name",
    # Government documents
    "aadhaar", "pan", "passport", "driving_licence", "voter_id", "fake_id_card",
    # Threat / coercion
    "threats", "blackmail", "sextortion", "digital_arrest", "legal_threats", "arrest_threats",
    "blackmail_indicator", "sextortion_indicator", "account_compromised",
    "impersonation_indicator", "threat_detected", "threat_type",
    # Evidence flags (stored as field entries too)
    "screenshots", "call_recordings", "chat_screenshot_mentioned",
    "bank_statement", "transaction_receipt", "email_evidence", "video_recording",
    # Analysis
    "attack_method", "scam_pattern", "victim_impact", "crypto_type", "account_id",
    # --- Phishing / BEC ---
    "sender_email", "recipient_email", "suspicious_domain",
    "attachment_name", "attachment_type", "impersonated_org",
    # AI / deepfake
    "cloned_voice", "cloned_video", "biometric_manipulation",
    "impersonated_person", "ai_generation_method",
    # Courier / remote-access scam
    "courier_company", "illegal_items_accused", "amount_paid", "remote_app", "suspect_phone",
    # BEC / account-takeover
    "spoofed_email", "documents_stolen", "stolen_aadhaar", "stolen_pan",
    "impersonator_details", "account_type", "platform_name", "recovery_details_changed",
    # Ransomware
    "ransomware_name", "os_affected",
]


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def extract_entities(description: str) -> Dict[str, Any]:
    """
    Extract cybercrime incident entities from natural language description.
    Uses a single Gemini 2.5 Flash structured call, falling back to a
    comprehensive local regex extractor if Gemini is unavailable.
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
                "audio_mentioned": False,
            },
            "warnings": ["Empty description provided."],
            "traceable_identifiers": {},
            "complaint_readiness_score": 0,
            "priority_level": "LOW",
        }

    # 1. Attempt Gemini structured extraction (single call)
    try:
        gemini_result = _extract_with_gemini(description_clean)
        if gemini_result:
            return run_post_extraction_validation(gemini_result, description_clean)
    except Exception as e:
        logger.warning(f"Gemini entity extraction failed: {e}. Falling back to regex backup extractor.")

    # 2. Fallback to Regex extraction
    fallback_result = _extract_fallback_regex(description_clean)
    return run_post_extraction_validation(fallback_result, description_clean)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _map_detail(detail) -> Dict[str, Any]:
    """Convert an ExtractedFieldDetail (model or dict) to our internal dict."""
    if detail is None:
        return {"value": None, "source": None, "source_text": None,
                "extraction_method": "gemini", "needs_review": False, "confidence": 0}

    if hasattr(detail, "model_dump"):
        detail = detail.model_dump()

    if not isinstance(detail, dict):
        return {"value": None, "source": None, "source_text": None,
                "extraction_method": "gemini", "needs_review": False, "confidence": 0}

    v = detail.get("value")
    if v is None:
        return {"value": None, "source": None, "source_text": None,
                "extraction_method": "gemini", "needs_review": False, "confidence": 0}

    v = str(v)
    raw_c = detail.get("confidence", 85)
    try:
        c = float(raw_c) if raw_c is not None else 85.0
        if 0.0 < c <= 1.0:
            c = c * 100
        c = int(c)
    except (ValueError, TypeError):
        c = 85

    s = str(detail.get("source_text") or detail.get("source") or v)
    return {"value": v, "source": s, "source_text": s,
            "extraction_method": "gemini", "needs_review": False, "confidence": c}


def _null_field(method: str = "gemini") -> Dict[str, Any]:
    return {"value": None, "source": None, "source_text": None,
            "extraction_method": method, "needs_review": False, "confidence": 0}


def _extract_root_domain(domain_str: str) -> str:
    """Return the registrable root domain (e.g. 'compliance-portal.net')."""
    d = domain_str.lower().strip().split("/")[0].split(":")[0]
    parts = d.split(".")
    if len(parts) < 2:
        return d
    if len(parts) >= 3 and parts[-2] in {"com", "co", "org", "gov", "ac", "net", "res", "edu"}:
        if parts[-1] in {"in", "uk", "us", "ca", "au", "nz", "jp"}:
            return ".".join(parts[-3:])
    return ".".join(parts[-2:])


# ---------------------------------------------------------------------------
# Gemini single-call extractor
# ---------------------------------------------------------------------------

def _extract_with_gemini(description: str) -> Optional[Dict[str, Any]]:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a Senior Cyber Crime Investigation Officer working for the Indian Police.
Your task is NOT keyword extraction — it is complaint understanding and evidence extraction.
Read the cybercrime complaint like a REAL INVESTIGATOR.

INVESTIGATION PROCESS
Before extracting anything:
1. Identify Victim (name, mobile, email, city/state)
2. Identify Suspect (name, mobile, UPI, bank account, social media, website)
3. Identify Scam Pattern (fraud type)
4. Identify Timeline (date, time, duration)
5. Identify Financial Loss (lost, demanded, invested, bait)
6. Identify Threats / Coercion (blackmail, digital arrest, sextortion, ransomware)
7. Identify Platform Used (WhatsApp, Telegram, Email, Phone, Instagram, etc.)
8. Identify Evidence Mentioned (screenshots, receipts, recordings)
9. Identify Phishing Indicators (sender email, suspicious domain, attachments, impersonated org)
10. Identify Attack Method

EXTRACTION RULES
- Extract ONLY information EXPLICITLY PRESENT in the description.
- Never guess. Never infer unsupported values.
- If a value is absent, return null.
- Confidence = 0–100 integer (90–100 for verified presence, 60–80 moderate, <50 uncertain).

PHISHING / EMAIL FRAUD RULES (critical)
- sender_email: The email address FROM WHICH the phishing / fraud email was received.
  A look-alike domain email (e.g. no-reply@incometax.gov.in.compliance-portal.net) IS the sender_email.
- suspicious_domain: The root domain used in the phishing email.
- attachment_name: Any file attached to the email (PDF, DOC, EXE, APK, etc.).
- impersonated_org: The organisation being impersonated (Income Tax Dept, TRAI, CBI, RBI, FedEx, etc.).
- Always extract incident_date and incident_time if mentioned.

AMOUNT REASONING (very important)
Distinguish: bait_payment (lure), amount_lost (actual loss), amount_demanded (ransom/threat demand).
For percentage demands: calculate the absolute rupee value.

VICTIM VS SUSPECT SEPARATION
Never mix victim and suspect information.

Analyse this description:
\"\"\"{description}\"\"\"

Return your response in structured JSON matching the schema. Do NOT wrap in markdown. Raw JSON only.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeminiExtractionResponse,
            temperature=0.0,
        ),
    )

    try:
        data = json.loads(response.text)
    except Exception as e:
        logger.error(f"Failed to parse Gemini JSON: {e}. Raw: {response.text[:300]}")
        return None

    extracted_fields: Dict[str, Any] = {}
    confidence_scores: Dict[str, int] = {}

    # Initialise every field to null so the response is always complete
    for f in ALL_EXTRACTION_FIELDS:
        extracted_fields[f] = _null_field("gemini")
        confidence_scores[f] = 0

    def _set(key: str, detail):
        mapped = _map_detail(detail)
        extracted_fields[key] = mapped
        confidence_scores[key] = mapped["confidence"]

    # --- Victim ---
    victim = data.get("victim") or {}
    _set("victim_name", victim.get("name"))
    _set("victim_mobile", victim.get("mobile"))
    _set("victim_phone", victim.get("mobile"))
    _set("victim_email", victim.get("email"))
    _set("victim_gender", victim.get("gender"))
    _set("victim_state", victim.get("state"))
    _set("victim_city", victim.get("city"))
    _set("suspect_social_media_id", victim.get("social_media_id"))  # victim's compromised handle

    # --- Suspect ---
    suspect = data.get("suspect") or {}
    _set("suspect_name", suspect.get("name"))
    _set("suspect_mobile", suspect.get("mobile"))
    _set("suspect_phone_numbers", suspect.get("mobile"))
    _set("suspect_upi", suspect.get("upi"))
    _set("suspect_upi_ids", suspect.get("upi"))
    _set("suspect_account_number", suspect.get("account_number"))
    _set("suspect_bank_accounts", suspect.get("account_number"))
    _set("suspect_social_media_handles", suspect.get("social_media_id"))
    _set("website_url", suspect.get("website_url"))
    _set("suspect_websites", suspect.get("website_url"))

    # --- Platform ---
    _set("platform", data.get("platform"))
    _set("fraud_platform", data.get("platform"))
    _set("fraud_channel", data.get("platform"))

    # --- Financial ---
    _set("amount_lost", data.get("amount_lost"))
    _set("amount_demanded", data.get("amount_demanded"))
    fin = data.get("financial_identifiers") or {}
    _set("upi_id", fin.get("upi_id"))
    _set("account_number", fin.get("account_number"))
    _set("transaction_id", fin.get("transaction_id"))
    _set("reference_number", fin.get("reference_number"))
    _set("utr_number", fin.get("utr_number"))

    # --- Phishing ---
    phishing = data.get("phishing") or {}
    _set("sender_email", phishing.get("sender_email"))
    _set("recipient_email", phishing.get("recipient_email"))
    _set("suspicious_domain", phishing.get("suspicious_domain"))
    _set("attachment_name", phishing.get("attachment_name"))
    _set("attachment_type", phishing.get("attachment_type"))
    _set("impersonated_org", phishing.get("impersonated_org"))
    _set("website_url", phishing.get("phishing_url") if not extracted_fields["website_url"]["value"] else phishing.get("phishing_url"))

    # --- Incident context ---
    _set("incident_date", data.get("incident_date"))
    _set("incident_time", data.get("incident_time"))

    # --- Identity / claimed ---
    _set("claimed_identity", data.get("claimed_identity"))

    # --- Crypto ---
    _set("crypto_type", data.get("crypto_type"))
    _set("crypto_wallet_address", data.get("crypto_wallet_address"))
    _set("suspect_wallet_addresses", data.get("crypto_wallet_address"))

    # --- Attack analysis ---
    _set("attack_method", data.get("attack_method"))
    _set("scam_pattern", data.get("scam_pattern"))

    # --- Digital arrest / ransomware ---
    _set("digital_arrest", data.get("digital_arrest"))
    _set("ransomware_name", data.get("ransomware_name"))
    _set("os_affected", data.get("os_affected"))

    # --- Deepfake / AI ---
    _set("cloned_voice", data.get("cloned_voice"))
    _set("cloned_video", data.get("cloned_video"))
    _set("biometric_manipulation", data.get("biometric_manipulation"))

    # --- Threats (list → string) ---
    threats_list = data.get("threats") or []
    if threats_list:
        t_str = "; ".join(str(t) for t in threats_list if t)
        if t_str:
            extracted_fields["threats"] = {
                "value": t_str, "source": t_str, "source_text": t_str,
                "extraction_method": "gemini", "needs_review": False, "confidence": 85,
            }
            confidence_scores["threats"] = 85

    # --- Evidence flags ---
    evidence_list = data.get("evidence") or []
    evidence_lower = [str(e).lower() for e in evidence_list]

    screenshot_mentioned = any(k in str(evidence_lower) for k in ["screenshot", "screen shot", "photo evidence"])
    receipt_mentioned = any(k in str(evidence_lower) for k in ["receipt", "bank receipt", "slip"])
    chat_mentioned = any(k in str(evidence_lower) for k in ["chat", "whatsapp chat"])
    video_mentioned = any(k in str(evidence_lower) for k in ["video", "clip", "recording"])
    audio_mentioned = any(k in str(evidence_lower) for k in ["audio", "voice", "call recording"])

    return {
        "extracted_fields": extracted_fields,
        "confidence_scores": confidence_scores,
        "evidence_flags": {
            "screenshot_mentioned": screenshot_mentioned,
            "bank_receipt_mentioned": receipt_mentioned,
            "chat_screenshot_mentioned": chat_mentioned,
            "video_mentioned": video_mentioned,
            "audio_mentioned": audio_mentioned,
        },
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Phone number context classifier
# ---------------------------------------------------------------------------

def classify_phone_number_context(number: str, description: str) -> str:
    """Return 'victim', 'suspect', or 'ambiguous' based on surrounding text."""
    text = description.lower()
    escaped = re.escape(number)
    matches = list(re.finditer(escaped, text))
    if not matches:
        return "ambiguous"

    victim_score = 0
    suspect_score = 0
    victim_kws = ["my", "i am", "victim", "contact me", "my phone", "my mobile", "my number", "contact number"]
    suspect_kws = [
        "fraudster", "scammer", "hacker", "suspect", "accused", "cheat", "scam",
        "called from", "got call", "he use", "she use", "demanded", "cheated",
        "whatsapp number", "fraudster mobile", "scammer mobile",
        "fraudster number", "scammer number", "accused number",
    ]
    for m in matches:
        ctx = text[max(0, m.start() - 50): m.end() + 10]
        for kw in victim_kws:
            if kw in ctx:
                victim_score += 1
        for kw in suspect_kws:
            if kw in ctx:
                suspect_score += 1

    if suspect_score > victim_score:
        return "suspect"
    if victim_score > suspect_score:
        return "victim"
    return "ambiguous"


# ---------------------------------------------------------------------------
# Comprehensive regex fallback extractor
# ---------------------------------------------------------------------------

def _extract_fallback_regex(description: str) -> Dict[str, Any]:  # noqa: C901
    text = description.lower()
    extracted_fields: Dict[str, Any] = {}
    confidence_scores: Dict[str, int] = {}
    warnings: List[str] = []

    # Initialise all fields to null
    for f in ALL_EXTRACTION_FIELDS:
        extracted_fields[f] = {
            "value": None, "source": None, "source_text": None,
            "extraction_method": "regex", "needs_review": False, "confidence": 0,
        }
        confidence_scores[f] = 0

    evidence_flags = {
        "screenshot_mentioned": False,
        "bank_receipt_mentioned": False,
        "chat_screenshot_mentioned": False,
        "video_mentioned": False,
        "audio_mentioned": False,
    }

    mobiles: List[str] = []

    # ------------------------------------------------------------------
    # 1. Mobile Numbers (Indian 10-digit)
    # ------------------------------------------------------------------
    mobile_matches = re.findall(r"\b[6-9]\d{9}\b", description)
    for m in mobile_matches:
        if m not in mobiles:
            mobiles.append(m)

    if mobiles:
        classified = [(m, classify_phone_number_context(m, description)) for m in mobiles]
        victims = [m for m, t in classified if t == "victim"]
        suspects = [m for m, t in classified if t == "suspect"]
        ambiguous = [m for m, t in classified if t == "ambiguous"]

        if victims:
            v = victims[0]
            extracted_fields["victim_mobile"] = {"value": v, "source": v, "source_text": v, "extraction_method": "regex", "needs_review": False, "confidence": 90}
            confidence_scores["victim_mobile"] = 90
        if suspects:
            s = suspects[0]
            extracted_fields["suspect_mobile"] = {"value": s, "source": s, "source_text": s, "extraction_method": "regex", "needs_review": False, "confidence": 90}
            confidence_scores["suspect_mobile"] = 90

        has_suspect_phrase = any(kw in text for kw in ["fraudster number", "scammer number", "hacker number", "suspect mobile", "accused number", "fraudster mobile", "scammer mobile"])

        if not extracted_fields["victim_mobile"]["value"] and ambiguous:
            m = ambiguous.pop(0)
            if has_suspect_phrase:
                extracted_fields["suspect_mobile"] = {"value": m, "source": m, "source_text": m, "extraction_method": "regex", "needs_review": False, "confidence": 85}
                confidence_scores["suspect_mobile"] = 85
            else:
                extracted_fields["victim_mobile"] = {"value": m, "source": m, "source_text": m, "extraction_method": "regex", "needs_review": False, "confidence": 85}
                confidence_scores["victim_mobile"] = 85

        if not extracted_fields["suspect_mobile"]["value"] and ambiguous:
            m = ambiguous.pop(0)
            extracted_fields["suspect_mobile"] = {"value": m, "source": m, "source_text": m, "extraction_method": "regex", "needs_review": False, "confidence": 85}
            confidence_scores["suspect_mobile"] = 85

    # ------------------------------------------------------------------
    # 2. Emails — with enhanced phishing / sender context detection
    # ------------------------------------------------------------------
    emails = re.findall(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", description)
    if emails:
        for e in emails:
            e_lower = e.lower()

            # --- Determine role ---
            is_noreply = e_lower.startswith("no-reply@") or e_lower.startswith("noreply@")

            # Context window: 80 chars before email, 60 chars after
            pos = description.lower().find(e_lower)
            pre_ctx = description[max(0, pos - 80): pos].lower() if pos >= 0 else ""
            post_ctx = description[pos: min(len(description), pos + len(e) + 60)].lower() if pos >= 0 else ""

            sender_signals = (
                is_noreply
                or any(kw in pre_ctx for kw in [
                    "received email from", "email from", "received an email",
                    "seemingly from", "email seemingly from", "received from",
                    "an email from", "mail from", "received a mail",
                ])
                or any(kw in post_ctx for kw in ["phishing", "look-alike", "identified as", "now identified"])
            )
            victim_signals = any(kw in pre_ctx for kw in [
                "my email", "my gmail", "my mail", "contact me at", "my address",
            ])

            if sender_signals:
                if not extracted_fields["sender_email"]["value"]:
                    extracted_fields["sender_email"] = {"value": e, "source": e, "source_text": e, "extraction_method": "regex", "needs_review": False, "confidence": 90}
                    confidence_scores["sender_email"] = 90
            elif victim_signals:
                if not extracted_fields["victim_email"]["value"]:
                    extracted_fields["victim_email"] = {"value": e, "source": e, "source_text": e, "extraction_method": "regex", "needs_review": False, "confidence": 90}
                    confidence_scores["victim_email"] = 90
            else:
                # Ambiguous — use generalised suspect keyword check
                has_suspect_kws = any(kw in text for kw in [
                    "fraudster email", "scammer email", "hacker email",
                    "suspect email", "email claiming",
                ])
                if not has_suspect_kws and not extracted_fields["victim_email"]["value"]:
                    extracted_fields["victim_email"] = {"value": e, "source": e, "source_text": e, "extraction_method": "regex", "needs_review": False, "confidence": 85}
                    confidence_scores["victim_email"] = 85

    # Auto-extract suspicious_domain from sender_email
    sender_val = extracted_fields.get("sender_email", {}).get("value")
    if sender_val and "@" in sender_val:
        domain_part = sender_val.split("@")[-1]
        susp = _extract_root_domain(domain_part)
        common_providers = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "zoho.com", "rediffmail.com"}
        if susp not in common_providers:
            extracted_fields["suspicious_domain"] = {"value": susp, "source": domain_part, "source_text": domain_part, "extraction_method": "regex", "needs_review": False, "confidence": 95}
            confidence_scores["suspicious_domain"] = 95

    # ------------------------------------------------------------------
    # 3. UPI IDs
    # ------------------------------------------------------------------
    all_upi = re.findall(r"\b[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+\b", description)
    upi_ids = [u for u in all_upi if u not in emails]

    if upi_ids:
        classified_upis = []
        for u in upi_ids:
            escaped = re.escape(u)
            matches = list(re.finditer(escaped, text))
            u_type = "ambiguous"
            if matches:
                vs = 0; ss = 0
                vkws = ["my upi", "my side", "sender upi", "my account", "from my upi", "sent from my upi"]
                skws = ["sent to", "paid to", "transferred to", "beneficiary", "fraudster upi",
                        "scammer upi", "cheat upi", "suspect upi", "receiver upi", "accused upi",
                        "sent money to", "paid money to", "transferred money to",
                        "send to", "pay to", "transfer to"]
                for m in matches:
                    ctx = text[max(0, m.start() - 50): m.end() + 10]
                    for kw in vkws:
                        if kw in ctx: vs += 1
                    for kw in skws:
                        if kw in ctx: ss += 1
                if ss > vs: u_type = "suspect"
                elif vs > ss: u_type = "victim"
            classified_upis.append((u, u_type))

        v_upis = [u for u, t in classified_upis if t == "victim"]
        s_upis = [u for u, t in classified_upis if t == "suspect"]
        a_upis = [u for u, t in classified_upis if t == "ambiguous"]

        if v_upis:
            extracted_fields["upi_id"] = {"value": v_upis[0], "source": v_upis[0], "source_text": v_upis[0], "extraction_method": "regex", "needs_review": False, "confidence": 90}
            confidence_scores["upi_id"] = 90
        if s_upis:
            extracted_fields["suspect_upi"] = {"value": s_upis[0], "source": s_upis[0], "source_text": s_upis[0], "extraction_method": "regex", "needs_review": False, "confidence": 90}
            confidence_scores["suspect_upi"] = 90

        if not extracted_fields["upi_id"]["value"] and a_upis:
            u = a_upis.pop(0)
            has_skws = any(kw in text for kw in ["sent to", "paid to", "transferred to", "beneficiary", "fraudster", "scammer", "suspect"])
            if has_skws:
                extracted_fields["suspect_upi"] = {"value": u, "source": u, "source_text": u, "extraction_method": "regex", "needs_review": False, "confidence": 85}
                confidence_scores["suspect_upi"] = 85
            else:
                extracted_fields["upi_id"] = {"value": u, "source": u, "source_text": u, "extraction_method": "regex", "needs_review": False, "confidence": 85}
                confidence_scores["upi_id"] = 85

        if not extracted_fields["suspect_upi"]["value"] and a_upis:
            u = a_upis.pop(0)
            extracted_fields["suspect_upi"] = {"value": u, "source": u, "source_text": u, "extraction_method": "regex", "needs_review": False, "confidence": 85}
            confidence_scores["suspect_upi"] = 85

    # ------------------------------------------------------------------
    # 4. Bank Account Numbers
    # ------------------------------------------------------------------
    acc_matches = re.findall(r"\b\d{9,18}\b", description)
    accs = [a for a in acc_matches if a not in mobiles]

    if accs:
        classified_accs = []
        for a in accs:
            escaped = re.escape(a)
            matches = list(re.finditer(escaped, text))
            a_type = "ambiguous"
            if matches:
                vs = 0; ss = 0
                vkws = ["my account", "my bank account", "debited from", "my bank", "savings account", "from my account"]
                skws = ["sent to account", "transferred to account", "beneficiary account",
                        "fraudster account", "scammer account", "suspect account", "accused account",
                        "hacker account", "sent money to", "transferred to", "paid to",
                        "sent to", "send to", "transfer to", "pay to"]
                for m in matches:
                    ctx = text[max(0, m.start() - 50): m.end() + 10]
                    for kw in vkws:
                        if kw in ctx: vs += 1
                    for kw in skws:
                        if kw in ctx: ss += 1
                if ss > vs: a_type = "suspect"
                elif vs > ss: a_type = "victim"
            classified_accs.append((a, a_type))

        v_accs = [a for a, t in classified_accs if t == "victim"]
        s_accs = [a for a, t in classified_accs if t == "suspect"]
        a_accs = [a for a, t in classified_accs if t == "ambiguous"]

        if v_accs:
            extracted_fields["account_number"] = {"value": v_accs[0], "source": v_accs[0], "source_text": v_accs[0], "extraction_method": "regex", "needs_review": False, "confidence": 90}
            confidence_scores["account_number"] = 90
        if s_accs:
            extracted_fields["suspect_account_number"] = {"value": s_accs[0], "source": s_accs[0], "source_text": s_accs[0], "extraction_method": "regex", "needs_review": False, "confidence": 90}
            confidence_scores["suspect_account_number"] = 90

        if not extracted_fields["account_number"]["value"] and a_accs:
            a = a_accs.pop(0)
            has_skws = any(kw in text for kw in ["sent to account", "transferred to account", "beneficiary account", "fraudster", "scammer"])
            if has_skws:
                extracted_fields["suspect_account_number"] = {"value": a, "source": a, "source_text": a, "extraction_method": "regex", "needs_review": False, "confidence": 85}
                confidence_scores["suspect_account_number"] = 85
            else:
                extracted_fields["account_number"] = {"value": a, "source": a, "source_text": a, "extraction_method": "regex", "needs_review": False, "confidence": 85}
                confidence_scores["account_number"] = 85

        if not extracted_fields["suspect_account_number"]["value"] and a_accs:
            a = a_accs.pop(0)
            extracted_fields["suspect_account_number"] = {"value": a, "source": a, "source_text": a, "extraction_method": "regex", "needs_review": False, "confidence": 85}
            confidence_scores["suspect_account_number"] = 85

    # ------------------------------------------------------------------
    # 5. Transaction IDs / UTR
    # ------------------------------------------------------------------
    potential_txs = re.findall(r"\b[A-Za-z0-9]{12,22}\b", description)
    txs = [t for t in potential_txs if not re.match(r"^\d{10}$", t) and any(c.isdigit() for c in t)]
    if txs:
        extracted_fields["transaction_id"] = {"value": txs[0], "source": txs[0], "source_text": txs[0], "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["transaction_id"] = 85

    # ------------------------------------------------------------------
    # 6. Cybercrime Indicators
    # ------------------------------------------------------------------
    account_comp_kws = ["hacked", "hack", "compromised", "takeover", "hijacked", "access lost", "blocked me out"]
    blackmail_kws = ["blackmail", "blackmailing", "threat", "threatening", "leak", "demand money", "extort"]
    sextortion_kws = ["sextortion", "nude", "naked", "intimate video", "leak nude", "intimate call",
                      "nude call", "nude photo", "nude video", "private video", "leak private video"]
    impersonation_kws = ["fake profile", "fake account", "impersonating", "impersonation",
                         "using my name", "using my photo", "fake facebook", "fake instagram",
                         "duplicate profile", "duplicate account", "impersonate"]

    account_compromised = any(w in text for w in account_comp_kws)
    blackmail_indicator = any(w in text for w in blackmail_kws)
    sextortion_indicator = any(w in text for w in sextortion_kws)
    impersonation_indicator = any(w in text for w in impersonation_kws)
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

    for ind_key, ind_val in [
        ("account_compromised", account_compromised),
        ("blackmail_indicator", blackmail_indicator),
        ("sextortion_indicator", sextortion_indicator),
        ("impersonation_indicator", impersonation_indicator),
        ("threat_detected", threat_detected),
    ]:
        extracted_fields[ind_key] = {"value": ind_val, "source": "Yes" if ind_val else "No", "source_text": "Yes" if ind_val else "No", "extraction_method": "regex", "needs_review": False, "confidence": 85 if ind_val else 0}
        confidence_scores[ind_key] = 85 if ind_val else 0

    extracted_fields["threat_type"] = {"value": threat_type_val, "source": threat_type_val, "source_text": threat_type_val, "extraction_method": "regex", "needs_review": False, "confidence": 85 if threat_type_val else 0}
    confidence_scores["threat_type"] = 85 if threat_type_val else 0

    # ------------------------------------------------------------------
    # 7. Amount Lost vs. Demanded
    # ------------------------------------------------------------------
    amount_pattern = (
        r"(?:lost|loss|losses|lose|losing|paid|pay|payment|payments|paying|sent|send|sending|"
        r"transferred|transfer|transfers|transferring|debited|debit|debits|demand|demands|demanding|"
        r"demanded|asking\s+for|ask\s+for|deposited|deposit|deposits|depositing|invested|invest|invests|"
        r"investing|rs\.?|rupees|inr|₹)"
        r"\s*(?:of\s+|a\s+|an\s+|the\s+|payment\s+|payments\s+|sum\s+|amount\s+|charge\s+|charges\s+)*"
        r"\s*(?:rs\.?|rupees|inr|₹)?"
        r"\s*(\d+(?:,\d{2,3})*(?:\.\d+)?)"
        r"\s*(%|percent|bitcoin|btc|eth|usdt|dollars?|usd|\$|coins?)?"
    )
    amount_matches = []
    for m in re.finditer(amount_pattern, description, re.IGNORECASE):
        val = m.group(1)
        clean_val = re.sub(r"[^\d.]", "", val)
        matched_str = m.group(0)
        # Determine currency
        currency = "INR"
        suffix = m.group(2)
        if suffix:
            currency = suffix
        else:
            ml = matched_str.lower()
            if "₹" in matched_str: currency = "₹"
            elif "inr" in ml: currency = "INR"
            elif "rs" in ml: currency = "Rs"
            elif "rupees" in ml: currency = "Rupees"

        ctx = description[max(0, m.start() - 100): m.end()].lower()
        is_demand = any(w in ctx for w in ["demand", "demanded", "demanding", "threat", "asking", "pay", "loan", "asking for", "request", "requested"])
        is_lost = any(w in ctx for w in ["lost", "paid", "transferred", "transfer", "debited", "loss", "deposited", "deposit", "invested", "invest"])
        if "sent" in ctx:
            for pos in [i for i in range(len(ctx)) if ctx.startswith("sent", i)]:
                sc = ctx[pos: pos + 50]
                if not any(w in sc for w in ["link", "apk", "file", "message", "photo", "video", "otp", "code", "request", "sms", "text"]):
                    is_lost = True
                    break
        amount_matches.append((clean_val, currency, m.group(0), is_lost, is_demand))

    lost_vals = [(v, c, s) for v, c, s, l, d in amount_matches if l]
    demand_vals = [(v, c, s) for v, c, s, l, d in amount_matches if d]

    if not lost_vals and not demand_vals and amount_matches:
        if blackmail_indicator or sextortion_indicator or impersonation_indicator:
            demand_vals = [(amount_matches[0][0], amount_matches[0][1], amount_matches[0][2])]
        else:
            lost_vals = [(amount_matches[0][0], amount_matches[0][1], amount_matches[0][2])]

    if lost_vals:
        extracted_fields["amount_lost"] = {"value": lost_vals[0][0], "amount": lost_vals[0][0], "currency": lost_vals[0][1], "source": lost_vals[0][2], "source_text": lost_vals[0][2], "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["amount_lost"] = 85

    if demand_vals:
        extracted_fields["amount_demanded"] = {"value": demand_vals[0][0], "amount": demand_vals[0][0], "currency": demand_vals[0][1], "source": demand_vals[0][2], "source_text": demand_vals[0][2], "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["amount_demanded"] = 85

    # ------------------------------------------------------------------
    # 8. Platform detection
    # ------------------------------------------------------------------
    platform_map = {
        "whatsapp": "WhatsApp", "instagram": "Instagram", "telegram": "Telegram",
        "facebook": "Facebook", "email": "Email", "phone call": "Phone Call",
        "upi": "UPI", "youtube": "YouTube", "linkedin": "LinkedIn",
        "twitter": "Twitter", "x": "X", "skype": "Skype", "zoom": "Zoom",
    }
    for p, proper in platform_map.items():
        if p in text:
            for pk in ["platform", "fraud_platform", "fraud_channel"]:
                extracted_fields[pk] = {"value": proper, "source": proper, "source_text": proper, "extraction_method": "regex", "needs_review": False, "confidence": 85}
                confidence_scores[pk] = 85
            break

    # ------------------------------------------------------------------
    # 9. Account / Social Media ID
    # ------------------------------------------------------------------
    # Use word boundaries to prevent "id" inside words like "avoid", "identified" from matching
    account_matches = re.findall(r"\b(?:account|profile|username|handle|user)\s+(?:name\s+)?(?:is\s+)?([a-zA-Z0-9._]+)", description, re.IGNORECASE)
    if not account_matches:
        # Also match explicit "account id" / "user id" constructs
        account_matches = re.findall(r"\b(?:account|user)\s+id\s+(?:is\s+)?([a-zA-Z0-9._]+)", description, re.IGNORECASE)
    if not account_matches:
        account_matches = re.findall(r"\B@([a-zA-Z0-9._]+)", description)

    if account_matches:
        noise = {"my", "the", "a", "his", "her", "their", "is", "was", "active", "compromised", "hacked"}
        cleaned = [a for a in account_matches if a.lower() not in noise and len(a) > 2]
        if cleaned:
            extracted_fields["account_id"] = {"value": cleaned[0], "source": cleaned[0], "source_text": cleaned[0], "extraction_method": "regex", "needs_review": False, "confidence": 85}
            confidence_scores["account_id"] = 85

    # ------------------------------------------------------------------
    # 10. Evidence Flags
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 11. Cryptocurrency Wallet Address
    # ------------------------------------------------------------------
    wallet_match = re.search(r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|0x[a-fA-F0-9]{40})\b", description)
    if wallet_match:
        wv = wallet_match.group(1)
        extracted_fields["crypto_wallet_address"] = {"value": wv, "source": wv, "source_text": wv, "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["crypto_wallet_address"] = 85

    # Cryptocurrency type
    crypto_type_val = None
    if "bitcoin" in text or " btc" in text or "btc " in text:
        crypto_type_val = "BTC"
    elif "ethereum" in text or " eth" in text:
        crypto_type_val = "ETH"
    elif "usdt" in text:
        crypto_type_val = "USDT"
    elif "bnb" in text:
        crypto_type_val = "BNB"
    elif "crypto" in text or "wallet" in text:
        crypto_type_val = "Other"

    if crypto_type_val:
        extracted_fields["crypto_type"] = {"value": crypto_type_val, "source": crypto_type_val, "source_text": crypto_type_val, "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["crypto_type"] = 85

    # ------------------------------------------------------------------
    # 12. Claimed Identity / Victim Name
    # ------------------------------------------------------------------
    claimed_match = re.search(
        r"\b(cbi\s+officer|police\s+officer|rbi\s+officer|ed\s+officer|customs\s+officer|"
        r"cyber\s+crime\s+officer|fedex\s+executive|fedex\s+agent|narcotics\s+officer|"
        r"narcotics\s+bureau\s+officer|income\s+tax\s+officer|enforcement\s+directorate\s+officer)\b",
        description, re.IGNORECASE,
    )
    if claimed_match:
        cv = claimed_match.group(1).title()
        extracted_fields["claimed_identity"] = {"value": cv, "source": claimed_match.group(0), "source_text": claimed_match.group(0), "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["claimed_identity"] = 85

    name_match = re.search(
        r"\b(?:my\s+name\s+is|i\s+am|this\s+is|myself)\s+([a-zA-Z]{3,20}(?:\s+[a-zA-Z]{3,20})?)\b",
        description, re.IGNORECASE,
    )
    if name_match:
        nv = name_match.group(1).strip()
        exclude = ["cbi", "police", "rbi", "ed", "customs", "cyber", "crime", "officer", "fedex", "narcotics", "bureau", "scammer", "hacker", "fraudster"]
        if not any(w in nv.lower() for w in exclude):
            extracted_fields["victim_name"] = {"value": nv, "source": name_match.group(0), "source_text": name_match.group(0), "extraction_method": "regex", "needs_review": False, "confidence": 85}
            confidence_scores["victim_name"] = 85

    # ------------------------------------------------------------------
    # 13. IP Address / Aadhaar / PAN / IFSC / APK / EXE
    # ------------------------------------------------------------------
    ip_match = re.search(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", description)
    if ip_match:
        extracted_fields["ip_address"] = {"value": ip_match.group(0), "source": ip_match.group(0), "source_text": ip_match.group(0), "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["ip_address"] = 85

    aadhaar_match = re.search(r"\b[2-9][0-9]{3}\s*[0-9]{4}\s*[0-9]{4}\b", description)
    if aadhaar_match:
        clean_a = re.sub(r"\s", "", aadhaar_match.group(0))
        extracted_fields["aadhaar"] = {"value": clean_a, "source": aadhaar_match.group(0), "source_text": aadhaar_match.group(0), "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["aadhaar"] = 85

    pan_match = re.search(r"\b[a-zA-Z]{5}[0-9]{4}[a-zA-Z]\b", description)
    if pan_match:
        extracted_fields["pan"] = {"value": pan_match.group(0).upper(), "source": pan_match.group(0), "source_text": pan_match.group(0), "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["pan"] = 85

    ifsc_match = re.search(r"\b[a-zA-Z]{4}0[a-zA-Z0-9]{6}\b", description)
    if ifsc_match:
        iv = ifsc_match.group(0).upper()
        extracted_fields["ifsc_code"] = {"value": iv, "source": iv, "source_text": iv, "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["ifsc_code"] = 85
        extracted_fields["suspect_ifsc_codes"] = extracted_fields["ifsc_code"]
        confidence_scores["suspect_ifsc_codes"] = 85

    apk_match = re.search(r"\b\w+\.apk\b", description, re.IGNORECASE)
    if apk_match:
        av = apk_match.group(0)
        extracted_fields["apk_name"] = {"value": av, "source": av, "source_text": av, "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["apk_name"] = 85
        extracted_fields["malware_file_name"] = extracted_fields["apk_name"]
        confidence_scores["malware_file_name"] = 85
        if not extracted_fields["attachment_name"]["value"]:
            extracted_fields["attachment_name"] = extracted_fields["apk_name"]
            confidence_scores["attachment_name"] = 85

    exe_match = re.search(r"\b\w+\.exe\b", description, re.IGNORECASE)
    if exe_match:
        ev = exe_match.group(0)
        extracted_fields["executable_name"] = {"value": ev, "source": ev, "source_text": ev, "extraction_method": "regex", "needs_review": False, "confidence": 85}
        confidence_scores["executable_name"] = 85
        extracted_fields["malware_file_name"] = extracted_fields["executable_name"]
        confidence_scores["malware_file_name"] = 85
        if not extracted_fields["attachment_name"]["value"]:
            extracted_fields["attachment_name"] = extracted_fields["executable_name"]
            confidence_scores["attachment_name"] = 85

    for doc_type in ["passport", "driving licence", "voter id", "fake id card"]:
        if doc_type in text:
            fk = doc_type.replace(" ", "_")
            extracted_fields[fk] = {"value": "Yes", "source": doc_type, "source_text": doc_type, "extraction_method": "regex", "needs_review": False, "confidence": 85}
            confidence_scores[fk] = 85

    # ------------------------------------------------------------------
    # 14. Document / PDF attachment detection (phishing)
    # ------------------------------------------------------------------
    if not extracted_fields["attachment_name"]["value"]:
        doc_match = re.search(
            r"\b([\w\-]+\.(?:pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|7z))\b",
            description, re.IGNORECASE,
        )
        if doc_match:
            att_name = doc_match.group(1)
            att_type = att_name.rsplit(".", 1)[-1].upper()
            extracted_fields["attachment_name"] = {"value": att_name, "source": doc_match.group(0), "source_text": doc_match.group(0), "extraction_method": "regex", "needs_review": False, "confidence": 90}
            confidence_scores["attachment_name"] = 90
            extracted_fields["attachment_type"] = {"value": att_type, "source": att_type, "source_text": att_type, "extraction_method": "regex", "needs_review": False, "confidence": 90}
            confidence_scores["attachment_type"] = 90

    # ------------------------------------------------------------------
    # 15. Incident Date extraction
    # ------------------------------------------------------------------
    date_patterns = [
        # "June 12, 2026" / "12 June 2026"
        r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[,\s]+\d{4})\b",
        r"\b((?:January|February|March|April|May|June|July|August|September|October|November|"
        r"December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)?"
        r"[,\s]+\d{4})\b",
        r"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b",
        r"\b(\d{4}-\d{2}-\d{2})\b",
    ]
    for dpat in date_patterns:
        dm = re.search(dpat, description, re.IGNORECASE)
        if dm:
            dv = dm.group(1).strip()
            extracted_fields["incident_date"] = {"value": dv, "source": dm.group(0), "source_text": dm.group(0), "extraction_method": "regex", "needs_review": False, "confidence": 90}
            confidence_scores["incident_date"] = 90
            break

    # ------------------------------------------------------------------
    # 16. Incident Time extraction
    # ------------------------------------------------------------------
    time_match = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\b", description, re.IGNORECASE)
    if time_match:
        tv = time_match.group(1).strip()
        extracted_fields["incident_time"] = {"value": tv, "source": time_match.group(0), "source_text": time_match.group(0), "extraction_method": "regex", "needs_review": False, "confidence": 90}
        confidence_scores["incident_time"] = 90

    # ------------------------------------------------------------------
    # 17. Impersonated Organisation (phishing / digital arrest context)
    # ------------------------------------------------------------------
    if not extracted_fields["impersonated_org"]["value"]:
        impersonated_patterns = [
            (r"\bincome\s+tax\s+(?:department|dept|authority|officer)?\b", "Income Tax Department"),
            (r"\btrai\b", "TRAI"),
            (r"\btdsat\b", "TDSAT"),
            (r"\bcbi\b", "CBI"),
            (r"\benforcement\s+directorate\b", "Enforcement Directorate"),
            (r"\bnarcotics\s+(?:bureau|control|department)\b", "Narcotics Control Bureau"),
            (r"\breserve\s+bank\s+of\s+india\b|\brbi\b", "Reserve Bank of India"),
            (r"\bcustoms\s+(?:department|authority|officer)?\b", "Customs Department"),
            (r"\bdhl\b", "DHL"),
            (r"\bfedex\b", "FedEx"),
            (r"\birctc\b", "IRCTC"),
            (r"\bsebi\b", "SEBI"),
            (r"\bnpci\b", "NPCI"),
            (r"\bcyber\s+crime\s+(?:cell|department|police)\b", "Cyber Crime Police"),
        ]
        impersonation_context_kws = [
            "claiming to be", "posing as", "impersonating", "from the", "seemingly from",
            "email from", "look-alike", "pretending", "fake", "fraudulent", "officer of",
            "official of", "compliance", "department of",
        ]
        for pattern, org_name in impersonated_patterns:
            org_match = re.search(pattern, text, re.IGNORECASE)
            if org_match:
                ctx_start = max(0, org_match.start() - 120)
                org_ctx = text[ctx_start: org_match.end() + 60]
                if any(kw in org_ctx for kw in impersonation_context_kws):
                    extracted_fields["impersonated_org"] = {"value": org_name, "source": org_match.group(0), "source_text": org_match.group(0), "extraction_method": "regex", "needs_review": False, "confidence": 90}
                    confidence_scores["impersonated_org"] = 90
                    extracted_fields["impersonation_indicator"] = {"value": True, "source": "Yes", "source_text": "Yes", "extraction_method": "regex", "needs_review": False, "confidence": 90}
                    confidence_scores["impersonation_indicator"] = 90
                    break

    # ------------------------------------------------------------------
    # 18. Specific threat types
    # ------------------------------------------------------------------
    threat_patterns = {
        "digital_arrest": ["digital arrest", "digitally arrested", "police custody online"],
        "arrest_threats": ["arrest", "police will arrest", "cbi arrest", "jail"],
        "legal_threats": ["court", "lawsuit", "legal action", "lawyer", "section"],
        "blackmail": ["blackmail", "blackmailed", "expose", "leak"],
        "sextortion": ["sextortion", "nude", "private video"],
    }
    for key_t, kws_t in threat_patterns.items():
        if any(w in text for w in kws_t):
            matched_w = next(w for w in kws_t if w in text)
            extracted_fields[key_t] = {"value": "Yes", "source": matched_w, "source_text": matched_w, "extraction_method": "regex", "needs_review": False, "confidence": 85}
            confidence_scores[key_t] = 85

    # ------------------------------------------------------------------
    # 19. Evidence type flags
    # ------------------------------------------------------------------
    evidence_types = {
        "screenshots": ["screenshot", "screenshots", "screen shot", "photo evidence"],
        "call_recordings": ["call recording", "recording", "audio recording", "voice recording"],
        "chat_screenshot_mentioned": ["chat", "whatsapp chat", "telegram chat", "message history"],
        "bank_statement": ["bank statement", "statement", "passbook"],
        "transaction_receipt": ["receipt", "transaction slip", "bank receipt"],
        "email_evidence": ["email", "emails", "gmail", "outlook"],
        "video_recording": ["video recording", "video clip", "recording of me"],
    }
    for key_e, kws_e in evidence_types.items():
        if any(w in text for w in kws_e):
            matched_w = next(w for w in kws_e if w in text)
            extracted_fields[key_e] = {"value": True, "source": matched_w, "source_text": matched_w, "extraction_method": "regex", "needs_review": False, "confidence": 85}
            confidence_scores[key_e] = 85

    # ------------------------------------------------------------------
    # Alias sync (primary ↔ alias)
    # ------------------------------------------------------------------
    def _sync(pk, ak):
        pv = extracted_fields.get(pk, {}).get("value")
        av = extracted_fields.get(ak, {}).get("value")
        if av and not pv:
            extracted_fields[pk] = extracted_fields[ak]
            confidence_scores[pk] = confidence_scores.get(ak, 0)
        elif pv and not av:
            extracted_fields[ak] = extracted_fields[pk]
            confidence_scores[ak] = confidence_scores.get(pk, 0)

    _sync("victim_phone", "victim_mobile")
    _sync("suspect_phone_numbers", "suspect_mobile")
    _sync("suspect_social_media_handles", "suspect_social_media_id")
    _sync("suspect_bank_accounts", "suspect_account_number")
    _sync("suspect_upi_ids", "suspect_upi")
    _sync("suspect_wallet_addresses", "crypto_wallet_address")
    _sync("suspect_websites", "website_url")

    return {
        "extracted_fields": extracted_fields,
        "confidence_scores": confidence_scores,
        "evidence_flags": evidence_flags,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Post-extraction validation + scoring
# ---------------------------------------------------------------------------

def run_post_extraction_validation(result: Dict[str, Any], description: str) -> Dict[str, Any]:  # noqa: C901
    extracted_fields = result.get("extracted_fields", {})
    confidence_scores = result.get("confidence_scores", {})
    warnings = result.get("warnings", [])
    text_lower = description.lower()

    # ------------------------------------------------------------------
    # 1. Never-guess check: verify extracted values actually appear in text
    # ------------------------------------------------------------------
    presence_fields = [
        "victim_mobile", "suspect_mobile", "upi_id", "suspect_upi", "transaction_id",
        "utr_number", "reference_number", "account_number", "suspect_account_number",
        "victim_email", "account_id", "suspect_social_media_id",
    ]
    for key in presence_fields:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip()
            clean_val = re.sub(r"[^\w]", "", val).lower()
            clean_desc = re.sub(r"[^\w]", "", description).lower()
            if clean_val and clean_val not in clean_desc:
                field["value"] = None
                field["source"] = None
                field["source_text"] = None
                field["confidence"] = 0
                confidence_scores[key] = 0

    # ------------------------------------------------------------------
    # 2. Forbidden-word rejection
    # ------------------------------------------------------------------
    FORBIDDEN_WORDS = {
        "administrator", "provided", "using", "profile", "friend", "request", "message",
        "video", "call", "account", "user", "person", "someone", "group", "admin",
    }
    identifier_fields = [
        "transaction_id", "utr_number", "reference_number", "account_number",
        "suspect_account_number", "account_id", "victim_name", "suspect_name",
        "suspect_social_media_id", "upi_id", "suspect_upi",
    ]
    for key in identifier_fields:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip().lower()
            if val in FORBIDDEN_WORDS:
                field["value"] = None
                field["confidence"] = 0
                confidence_scores[key] = 0
                msg = f"Forbidden word '{val}' rejected for {key.replace('_', ' ').title()}."
                if msg not in warnings:
                    warnings.append(msg)

    # ------------------------------------------------------------------
    # 3. Context-aware mobile re-classification
    # ------------------------------------------------------------------
    victim_mobile_val = extracted_fields.get("victim_mobile", {}).get("value")
    if victim_mobile_val:
        c_type = classify_phone_number_context(victim_mobile_val, description)
        suspect_phrases = ["fraudster number", "scammer number", "hacker number", "suspect mobile", "accused number", "fraudster mobile", "scammer mobile", "accused mobile"]
        has_suspect_phrase = any(kw in text_lower for kw in suspect_phrases)
        if c_type == "suspect" or (has_suspect_phrase and c_type != "victim"):
            if not extracted_fields.get("suspect_mobile", {}).get("value"):
                extracted_fields["suspect_mobile"] = dict(extracted_fields["victim_mobile"])
                confidence_scores["suspect_mobile"] = 90
            extracted_fields["victim_mobile"] = _null_field()
            confidence_scores["victim_mobile"] = 0
            warnings.append("Context indicates the mobile number belongs to the suspect. Reassigned to Suspect Mobile.")

    # ------------------------------------------------------------------
    # 4. Context-aware UPI re-classification
    # ------------------------------------------------------------------
    victim_upi_val = extracted_fields.get("upi_id", {}).get("value")
    if victim_upi_val:
        escaped = re.escape(victim_upi_val)
        u_type = "ambiguous"
        matches = list(re.finditer(escaped, text_lower))
        if matches:
            vs = 0; ss = 0
            vkws = ["my upi", "my side", "sender upi", "my account", "from my upi", "sent from my upi"]
            skws = ["sent to", "paid to", "transferred to", "beneficiary", "fraudster upi", "scammer upi",
                    "cheat upi", "suspect upi", "receiver upi", "accused upi",
                    "sent money to", "paid money to", "transferred money to",
                    "send to", "pay to", "transfer to"]
            for m in matches:
                ctx = text_lower[max(0, m.start() - 50): m.end() + 10]
                for kw in vkws:
                    if kw in ctx: vs += 1
                for kw in skws:
                    if kw in ctx: ss += 1
            if ss > vs: u_type = "suspect"
            elif vs > ss: u_type = "victim"
        if u_type == "suspect":
            if not extracted_fields.get("suspect_upi", {}).get("value"):
                extracted_fields["suspect_upi"] = dict(extracted_fields["upi_id"])
                confidence_scores["suspect_upi"] = 90
            extracted_fields["upi_id"] = _null_field()
            confidence_scores["upi_id"] = 0
            warnings.append("Context indicates the UPI ID belongs to the suspect. Reassigned to Suspect UPI.")

    # ------------------------------------------------------------------
    # 5. Context-aware account re-classification
    # ------------------------------------------------------------------
    victim_acc_val = extracted_fields.get("account_number", {}).get("value")
    if victim_acc_val:
        escaped = re.escape(victim_acc_val)
        a_type = "ambiguous"
        matches = list(re.finditer(escaped, text_lower))
        if matches:
            vs = 0; ss = 0
            vkws = ["my account", "my bank account", "debited from", "my bank", "savings account", "from my account"]
            skws = ["sent to account", "transferred to account", "beneficiary account",
                    "fraudster account", "scammer account", "suspect account", "accused account",
                    "hacker account", "sent money to", "transferred to", "paid to",
                    "sent to", "send to", "transfer to", "pay to"]
            for m in matches:
                ctx = text_lower[max(0, m.start() - 50): m.end() + 10]
                for kw in vkws:
                    if kw in ctx: vs += 1
                for kw in skws:
                    if kw in ctx: ss += 1
            if ss > vs: a_type = "suspect"
            elif vs > ss: a_type = "victim"
        if a_type == "suspect":
            if not extracted_fields.get("suspect_account_number", {}).get("value"):
                extracted_fields["suspect_account_number"] = dict(extracted_fields["account_number"])
                confidence_scores["suspect_account_number"] = 90
            extracted_fields["account_number"] = _null_field()
            confidence_scores["account_number"] = 0
            warnings.append("Context indicates the bank account number belongs to the suspect. Reassigned to Suspect Account Number.")

    # ------------------------------------------------------------------
    # 6. Sextortion validation
    # ------------------------------------------------------------------
    sext_field = extracted_fields.get("sextortion_indicator")
    if sext_field and sext_field.get("value") is True:
        intimate_kws = ["nude", "naked", "intimate", "private video", "sexual", "sextortion", "video call recording", "recording of me"]
        if not any(w in text_lower for w in intimate_kws):
            extracted_fields["sextortion_indicator"] = {"value": False, "source": "No", "source_text": "No", "extraction_method": sext_field.get("extraction_method", "regex"), "needs_review": False, "confidence": 0}
            confidence_scores["sextortion_indicator"] = 0
            extracted_fields["blackmail_indicator"] = {"value": True, "source": "Yes", "source_text": "Yes", "extraction_method": "regex", "needs_review": False, "confidence": 90}
            confidence_scores["blackmail_indicator"] = 90
            threat_type_field = extracted_fields.get("threat_type")
            if threat_type_field and threat_type_field.get("value") == "Sextortion":
                if "photo" in text_lower or "pic" in text_lower:
                    threat_type_field["value"] = "Photo Leak"
                elif "video" in text_lower:
                    threat_type_field["value"] = "Video Leak"
                else:
                    threat_type_field["value"] = "Blackmail"

    # ------------------------------------------------------------------
    # 7. Phishing email re-classification (Gemini may put it in victim_email)
    # ------------------------------------------------------------------
    victim_email_val = extracted_fields.get("victim_email", {}).get("value")
    if victim_email_val:
        e_lower_v = victim_email_val.lower()
        escaped_e = re.escape(victim_email_val)
        matches = list(re.finditer(escaped_e, text_lower))
        e_type = "ambiguous"
        if matches:
            vs = 0; ss = 0
            vkws = ["my email", "received at my", "received on my", "my address", "i use"]
            skws = ["from", "sent by", "sender", "received email from", "cheated by email",
                    "phishing email", "fake email", "invoice from", "seemingly from",
                    "received an email"]
            for m in matches:
                ctx = text_lower[max(0, m.start() - 60): m.end() + 10]
                for kw in vkws:
                    if kw in ctx: vs += 1
                for kw in skws:
                    if kw in ctx: ss += 1
            if ss > vs: e_type = "suspect"
            elif vs > ss: e_type = "victim"

        # Also auto-classify no-reply@ as sender
        is_noreply = e_lower_v.startswith("no-reply@") or e_lower_v.startswith("noreply@")
        if e_type == "suspect" or is_noreply:
            if not extracted_fields.get("sender_email", {}).get("value"):
                extracted_fields["sender_email"] = {
                    "value": victim_email_val,
                    "source": extracted_fields["victim_email"].get("source") or victim_email_val,
                    "source_text": extracted_fields["victim_email"].get("source_text") or victim_email_val,
                    "extraction_method": extracted_fields["victim_email"].get("extraction_method", "gemini"),
                    "needs_review": False,
                    "confidence": extracted_fields["victim_email"].get("confidence") or 90,
                }
                confidence_scores["sender_email"] = extracted_fields["sender_email"]["confidence"]
            extracted_fields["victim_email"] = _null_field()
            confidence_scores["victim_email"] = 0
            warnings.append("Context indicates the email address is from the sender/suspect. Reassigned to Sender Email.")

    # Auto-extract suspicious_domain from sender_email (works for Gemini path too)
    s_email = extracted_fields.get("sender_email", {}).get("value")
    if s_email and "@" in s_email:
        domain_part = s_email.split("@")[-1]
        susp_domain = _extract_root_domain(domain_part)
        common_providers = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "zoho.com", "rediffmail.com"}
        if susp_domain not in common_providers and not extracted_fields.get("suspicious_domain", {}).get("value"):
            extracted_fields["suspicious_domain"] = {
                "value": susp_domain,
                "source": s_email,
                "source_text": domain_part,
                "extraction_method": "hybrid",
                "needs_review": False,
                "confidence": 95,
            }
            confidence_scores["suspicious_domain"] = 95

    # ------------------------------------------------------------------
    # 8. Format validations
    # ------------------------------------------------------------------
    # Mobile: must be exactly 10 digits
    for key in ["victim_mobile", "suspect_mobile"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip()
            cleaned = re.sub(r"\D", "", val)
            if len(cleaned) == 12 and cleaned.startswith("91"):
                cleaned = cleaned[2:]
            elif len(cleaned) == 11 and cleaned.startswith("0"):
                cleaned = cleaned[1:]
            if len(cleaned) != 10:
                field["value"] = None
                field["needs_review"] = True
                field["confidence"] = 0
                confidence_scores[key] = 0
                msg = f"Invalid {key.replace('_', ' ').title()} '{val}': Must be 10 digits."
                if msg not in warnings:
                    warnings.append(msg)
            else:
                field["value"] = cleaned

    # Ambiguous mobile flag
    for key in ["victim_mobile", "suspect_mobile"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            c_type = classify_phone_number_context(field["value"], description)
            if c_type == "ambiguous":
                field["needs_review"] = True
                field["confidence"] = 50
                confidence_scores[key] = 50
                msg = f"Mobile context for {key.replace('_', ' ').title()} is ambiguous. Marked for review."
                if msg not in warnings:
                    warnings.append(msg)

    # Email format
    for key in ["victim_email"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", str(field["value"]).strip()):
                field["value"] = None
                field["needs_review"] = True
                field["confidence"] = 0
                confidence_scores[key] = 0
                warnings.append(f"Invalid Victim Email '{field.get('value')}': Must match email pattern.")

    # UPI: must have @
    for key in ["upi_id", "suspect_upi"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            if "@" not in str(field["value"]):
                field["value"] = None
                field["needs_review"] = True
                field["confidence"] = 0
                confidence_scores[key] = 0
                warnings.append(f"Invalid {key.replace('_', ' ').title()}: Must contain '@'.")

    # Transaction / UTR: must have digits
    for key in ["transaction_id", "utr_number", "reference_number"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            if not any(c.isdigit() for c in str(field["value"])):
                field["value"] = None
                field["needs_review"] = True
                field["confidence"] = 0
                confidence_scores[key] = 0

    # Username / social handle validation
    COMMON_WORDS = {
        "the", "and", "for", "you", "that", "this", "with", "have", "not", "but", "his", "her",
        "him", "she", "they", "them", "was", "were", "been", "has", "had", "are", "our", "your",
        "someone", "somebody", "nobody", "anybody", "people", "person", "friend", "profile",
        "account", "user", "username", "admin", "administrator", "using", "provided", "request",
        "message", "video", "call", "group", "hacker", "scammer", "fraudster", "victim", "suspect",
        # Common gerunds/verbs that could be captured after "account"
        "freezing", "frozen", "blocked", "locked", "hacked", "compromised", "encrypted",
        "demanded", "threatening", "claiming", "sharing", "posting", "depositing",
        "transferring", "investing", "receiving", "sending", "processing", "verifying",
        "avoiding", "prevent", "resolve", "settle", "payment", "transfer", "deposit",
        # Common nouns that would never be a username
        "discrepancy", "outstanding", "corporate", "official", "department", "officer",
        "number", "mobile", "phone", "bank", "credit", "debit", "online", "offline",
        "digital", "cyber", "crime", "police", "complaint", "report", "notice", "demand",
        "verification", "urgent", "immediate", "attachment", "attachment",
    }
    for key in ["victim_name", "suspect_name", "account_id", "suspect_social_media_id"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip().rstrip(".,;:!?")  # strip trailing punctuation
            field["value"] = val  # apply stripping
            if len(val) < 3 or val.lower() in COMMON_WORDS or val.lower() in FORBIDDEN_WORDS:
                field["value"] = None
                field["needs_review"] = True
                field["confidence"] = 0
                confidence_scores[key] = 0

    # Amount: must be numeric
    for key in ["amount_lost", "amount_demanded", "bait_payment"]:
        field = extracted_fields.get(key)
        if field and field.get("value"):
            val = str(field["value"]).strip()
            source_txt = str(field.get("source_text") or field.get("source") or "").lower()
            # Handle percentage demands
            if "%" in source_txt or "percent" in source_txt or val.endswith("%"):
                try:
                    pct = float(re.sub(r"[^\d.]", "", val))
                    if pct <= 100:
                        all_nums = [float(re.sub(r"[^\d.]", "", n)) for n in re.findall(r"\b\d+(?:,\d{2,3})*(?:\.\d+)?\b", description)]
                        large_nums = [n for n in all_nums if n > 100 and n != pct]
                        if large_nums:
                            base = max(large_nums)
                            calc = (pct / 100.0) * base
                            val = str(int(calc)) if calc.is_integer() else f"{calc:.2f}"
                except (ValueError, TypeError):
                    pass
            num_matches = re.findall(r"\d+(?:,\d{2,3})*(?:\.\d+)?", val)
            if num_matches:
                cleaned_num = re.sub(r"[^\d.]", "", num_matches[0])
                try:
                    float(cleaned_num)
                    field["value"] = cleaned_num
                    if "amount" in field:
                        field["amount"] = cleaned_num
                except ValueError:
                    field["value"] = None
                    field["confidence"] = 0
                    confidence_scores[key] = 0
            else:
                field["value"] = None
                field["confidence"] = 0
                confidence_scores[key] = 0

    # ------------------------------------------------------------------
    # 9. Crypto / claimed-identity fallback (regex safety net for Gemini path)
    # ------------------------------------------------------------------
    if not extracted_fields.get("crypto_wallet_address", {}).get("value"):
        wm = re.search(r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|0x[a-fA-F0-9]{40})\b", description)
        if wm:
            wv = wm.group(1)
            extracted_fields["crypto_wallet_address"] = {"value": wv, "source": wv, "source_text": wv, "extraction_method": "hybrid", "needs_review": False, "confidence": 85}
            confidence_scores["crypto_wallet_address"] = 85

    if not extracted_fields.get("claimed_identity", {}).get("value"):
        cm = re.search(
            r"\b(cbi\s+officer|police\s+officer|rbi\s+officer|ed\s+officer|customs\s+officer|"
            r"cyber\s+crime\s+officer|fedex\s+executive|fedex\s+agent|narcotics\s+officer|"
            r"narcotics\s+bureau\s+officer|income\s+tax\s+officer|enforcement\s+directorate\s+officer)\b",
            description, re.IGNORECASE,
        )
        if cm:
            cv = cm.group(1).title()
            extracted_fields["claimed_identity"] = {"value": cv, "source": cm.group(0), "source_text": cm.group(0), "extraction_method": "hybrid", "needs_review": False, "confidence": 85}
            confidence_scores["claimed_identity"] = 85

    if not extracted_fields.get("crypto_type", {}).get("value"):
        tl = text_lower
        cv = None
        if "bitcoin" in tl or " btc" in tl or "btc " in tl:
            cv = "BTC"
        elif "ethereum" in tl or " eth" in tl:
            cv = "ETH"
        elif "usdt" in tl:
            cv = "USDT"
        elif "bnb" in tl:
            cv = "BNB"
        elif "crypto" in tl or "wallet" in tl:
            cv = "Other"
        if cv:
            extracted_fields["crypto_type"] = {"value": cv, "source": cv, "source_text": cv, "extraction_method": "hybrid", "needs_review": False, "confidence": 85}
            confidence_scores["crypto_type"] = 85

    # ------------------------------------------------------------------
    # 10. Normalise all fields to consistent structure
    # ------------------------------------------------------------------
    for key in ALL_EXTRACTION_FIELDS:
        field = extracted_fields.get(key)
        if not field:
            field = {"value": None}
        if not isinstance(field, dict):
            field = {"value": field}
        if "extraction_method" not in field or not field["extraction_method"]:
            field["extraction_method"] = "gemini" if result.get("extracted_fields") and key in result.get("extracted_fields", {}) else "regex"
        field["needs_review"] = (field.get("needs_review") is True)
        if not field.get("source_text"):
            field["source_text"] = field.get("source") or field.get("value")
        if not field.get("source"):
            field["source"] = field.get("source_text") or field.get("value")
        if not field.get("confidence"):
            field["confidence"] = confidence_scores.get(key, 0)
        # Remove legacy "status" key
        field.pop("status", None)
        extracted_fields[key] = field

    # Final alias sync
    def _sync(pk, ak):
        pv = extracted_fields.get(pk, {}).get("value")
        av = extracted_fields.get(ak, {}).get("value")
        if av and not pv:
            extracted_fields[pk] = extracted_fields[ak]
            confidence_scores[pk] = confidence_scores.get(ak, 0)
        elif pv and not av:
            extracted_fields[ak] = extracted_fields[pk]
            confidence_scores[ak] = confidence_scores.get(pk, 0)

    _sync("victim_phone", "victim_mobile")
    _sync("suspect_phone_numbers", "suspect_mobile")
    _sync("suspect_social_media_handles", "suspect_social_media_id")
    _sync("suspect_bank_accounts", "suspect_account_number")
    _sync("suspect_upi_ids", "suspect_upi")
    _sync("suspect_wallet_addresses", "crypto_wallet_address")
    _sync("suspect_websites", "website_url")

    # ------------------------------------------------------------------
    # 11. Traceable Identifiers object
    # ------------------------------------------------------------------
    def _get_list_vals(key):
        f = extracted_fields.get(key, {})
        if f and f.get("value"):
            return [v.strip() for v in str(f["value"]).split(",") if v.strip()]
        return []

    traceable_identifiers = {
        "phone_numbers": list(set(_get_list_vals("suspect_phone_numbers"))),
        "emails": list(set(_get_list_vals("suspect_emails") + _get_list_vals("sender_email"))),
        "upi_ids": list(set(_get_list_vals("suspect_upi_ids"))),
        "bank_accounts": list(set(_get_list_vals("suspect_bank_accounts"))),
        "wallet_addresses": list(set(_get_list_vals("suspect_wallet_addresses"))),
        "social_handles": list(set(_get_list_vals("suspect_social_media_handles"))),
        "websites": list(set(_get_list_vals("suspect_websites") + _get_list_vals("suspect_urls"))),
        "domains": list(set(_get_list_vals("domain_name") + _get_list_vals("suspicious_domain"))),
        "ip_addresses": list(set(_get_list_vals("ip_address"))),
    }

    # ------------------------------------------------------------------
    # 12. NCRP Readiness Score (0–100)
    # ------------------------------------------------------------------
    readiness_points = 0

    # Financial identifiers (high weight — needed for fund freezing)
    if extracted_fields.get("suspect_phone_numbers", {}).get("value") or extracted_fields.get("victim_phone", {}).get("value"):
        readiness_points += 10  # Phone
    if extracted_fields.get("suspect_upi_ids", {}).get("value") or extracted_fields.get("upi_id", {}).get("value"):
        readiness_points += 15  # UPI
    if extracted_fields.get("suspect_bank_accounts", {}).get("value") or extracted_fields.get("account_number", {}).get("value"):
        readiness_points += 15  # Bank account
    if extracted_fields.get("transaction_id", {}).get("value") or extracted_fields.get("reference_number", {}).get("value"):
        readiness_points += 15  # Transaction ID
    if extracted_fields.get("screenshots", {}).get("value") or extracted_fields.get("chat_screenshot_mentioned", {}).get("value") or extracted_fields.get("transaction_receipt", {}).get("value"):
        readiness_points += 10  # Screenshot / receipt
    if extracted_fields.get("amount_lost", {}).get("value") or extracted_fields.get("amount_demanded", {}).get("value"):
        readiness_points += 10  # Amount
    if extracted_fields.get("platforms_used", {}).get("value") or extracted_fields.get("platform", {}).get("value"):
        readiness_points += 10  # Platform
    if extracted_fields.get("suspect_name", {}).get("value"):
        readiness_points += 5   # Suspect name
    if extracted_fields.get("suspect_emails", {}).get("value") or extracted_fields.get("victim_email", {}).get("value"):
        readiness_points += 5   # Email
    if extracted_fields.get("suspect_wallet_addresses", {}).get("value"):
        readiness_points += 15  # Crypto wallet

    # Phishing-specific evidence (meaningful even without financial loss)
    if extracted_fields.get("sender_email", {}).get("value"):
        readiness_points += 10   # Sender email is a key phishing artefact
    if extracted_fields.get("suspicious_domain", {}).get("value"):
        readiness_points += 10   # Suspicious domain
    if extracted_fields.get("attachment_name", {}).get("value"):
        readiness_points += 5    # Malicious attachment
    if extracted_fields.get("impersonated_org", {}).get("value"):
        readiness_points += 5    # Known impersonation target
    if extracted_fields.get("incident_date", {}).get("value"):
        readiness_points += 5    # Timestamped complaint

    complaint_readiness_score = min(100, readiness_points)

    # ------------------------------------------------------------------
    # 13. Priority Level
    # ------------------------------------------------------------------
    priority_level = "LOW"

    is_digital_arrest = (extracted_fields.get("digital_arrest", {}).get("value") == "Yes")
    is_ransomware = any(kw in text_lower for kw in ["ransomware", ".locked", "encrypted", "decryption"])
    is_csam = any(kw in text_lower for kw in ["child", "minor", "csam", "exploit"])

    lost_val_num = 0.0
    lost_field = extracted_fields.get("amount_lost")
    if lost_field and lost_field.get("value"):
        try:
            lost_val_num = float(lost_field["value"])
        except (ValueError, TypeError):
            pass
    is_large_loss = (lost_val_num >= 100000)

    is_sextortion = (extracted_fields.get("sextortion", {}).get("value") == "Yes" or
                     extracted_fields.get("sextortion_indicator", {}).get("value") is True)
    is_investment_scam = any(kw in text_lower for kw in ["investment", "trading scam", "crypto experts", "coinvibe"])
    is_loan_app = any(kw in text_lower for kw in ["loan app", "instant loan", "extortion"])
    is_blackmail = (extracted_fields.get("blackmail", {}).get("value") == "Yes" or
                    extracted_fields.get("blackmail_indicator", {}).get("value") is True)

    is_phishing_gov = (
        extracted_fields.get("sender_email", {}).get("value") and
        extracted_fields.get("impersonated_org", {}).get("value")
    )

    if is_digital_arrest or is_ransomware or is_large_loss or is_csam:
        priority_level = "CRITICAL"
    elif is_sextortion or is_investment_scam or is_loan_app or is_blackmail or is_phishing_gov:
        priority_level = "HIGH"
    elif lost_val_num > 0 or extracted_fields.get("threats", {}).get("value") or extracted_fields.get("sender_email", {}).get("value"):
        priority_level = "MEDIUM"

    result["extracted_fields"] = extracted_fields
    result["confidence_scores"] = confidence_scores
    result["warnings"] = warnings
    result["traceable_identifiers"] = traceable_identifiers
    result["complaint_readiness_score"] = complaint_readiness_score
    result["priority_level"] = priority_level
    return result
