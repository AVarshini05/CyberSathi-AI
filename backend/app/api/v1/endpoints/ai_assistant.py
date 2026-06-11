"""
AI Assistant API Endpoints.

Provides chat (text), voice (STT→Gemini→TTS), and session management endpoints
for the CCRMS AI-powered cybercrime complaint intake agent.

Voice providers (priority order):
  1. Browser Web Speech API (handled client-side — no server involvement)
  2. Sarvam AI (server-side fallback — used via /voice and /tts endpoints)

AI Brain: Gemini (with rule-based offline fallback)
"""

import datetime
import uuid
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, status
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.models.ai_session import AISession
from app.models.complaint import ComplaintCategory, ComplaintSubcategory, ComplaintQuestion
from app.services import sarvam_client, gemini_client
from pydantic import BaseModel

logger = logging.getLogger("ai_assistant_api")

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    confidence: Optional[float] = 1.0


class LanguageRequest(BaseModel):
    session_id: str
    language: str


class TTSRequest(BaseModel):
    text: str
    language: str


def get_optional_current_user(
    request: Request,
    db: Session = Depends(deps.get_db)
) -> Optional[User]:
    """Helper to extract current user from auth header if present, otherwise returns None."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        import jwt
        from app.core import security
        from app.schemas.token import TokenPayload
        from app.crud.crud_user import crud_user
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        user = crud_user.get(db, id=int(token_data.sub))
        return user
    except Exception:
        return None


@router.post("/start")
async def start_session(
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> Dict[str, Any]:
    """Initialize a new AI assistant session and generate default greeting."""
    session_id = str(uuid.uuid4())
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

    # Default language: English (en-IN)
    default_lang = "en-IN"

    greeting = (
        "Hello. I am your Cybercrime Complaint Officer. "
        "Please explain what happened in your own words. "
        "I will help you file your complaint step-by-step."
    )

    # Try to generate TTS audio (optional — never block on failure)
    audio_base64 = None
    try:
        audio_base64 = await sarvam_client.text_to_speech(greeting, default_lang)
    except Exception as e:
        logger.warning("Greeting TTS unavailable: %s", str(e)[:100])

    # Save session to DB
    session = AISession(
        id=session_id,
        user_id=current_user.id if current_user else None,
        state="GREETING",
        collected_data={},
        conversation_history=[{
            "role": "assistant",
            "text": greeting,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }],
        language=default_lang,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()

    return {
        "session_id": session_id,
        "greeting": greeting,
        "audio_base64": audio_base64,
        "audio_base_64": audio_base64,
        "language": default_lang
    }


def _get_session_form_data(session: AISession, db: Session) -> Dict[str, Any]:
    collected = session.collected_data or {}

    result = {
        "category_id": session.detected_category_id,
        "subcategory_id": session.detected_subcategory_id,
        "victim_name": collected.get("victim_name", ""),
        "victim_mobile": collected.get("victim_mobile", ""),
        "victim_email": collected.get("victim_email", ""),
        "victim_gender": collected.get("victim_gender", ""),
        "victim_state": collected.get("victim_state", ""),
        "victim_address": collected.get("victim_address", ""),
        "fraud_description": collected.get("fraud_description", ""),
        "is_anonymous": collected.get("is_anonymous", False),
        "suspect_name": collected.get("suspect_name", ""),
        "suspect_mobile": collected.get("suspect_mobile", ""),
        "suspect_email": collected.get("suspect_email", ""),
        "suspect_upi": collected.get("suspect_upi", ""),
        "suspect_url": collected.get("suspect_url", ""),
        "suspect_social_handle": collected.get("suspect_social_handle", ""),
        "suspect_details": collected.get("suspect_details", ""),
        "answers": []
    }

    if session.detected_subcategory_id:
        questions = db.query(ComplaintQuestion).filter(
            ComplaintQuestion.subcategory_id == session.detected_subcategory_id
        ).all()

        for q in questions:
            if q.field_name in collected:
                result["answers"].append({
                    "question_id": q.id,
                    "field_name": q.field_name,
                    "value": str(collected[q.field_name])
                })
    return result


def _get_conversation_state(session: AISession, db: Session, missing_fields: List[str]) -> Dict[str, Any]:
    collected = session.collected_data or {}

    sub_name = ""
    if session.detected_subcategory_id:
        sub = db.query(ComplaintSubcategory).filter(ComplaintSubcategory.id == session.detected_subcategory_id).first()
        if sub:
            sub_name = sub.name

    platform = collected.get("platform") or collected.get("platform_name") or collected.get("app_name") or ""
    username = collected.get("username") or collected.get("impersonator_handle") or collected.get("stalker_handle") or ""
    email = collected.get("victim_email") or collected.get("email_address") or ""
    phone = collected.get("victim_mobile") or collected.get("suspect_mobile") or collected.get("suspect_contact") or ""

    date_val = collected.get("transaction_date") or collected.get("last_access") or collected.get("start_date") or collected.get("uploaded_date") or ""
    time_val = ""
    if date_val and "T" in date_val:
        parts = date_val.split("T")
        date_val = parts[0]
        time_val = parts[1]

    amount_lost = collected.get("amount") or collected.get("total_lost") or collected.get("amount_demanded") or collected.get("amount_disbursed") or ""
    tx_id = collected.get("transaction_id") or collected.get("utr_number") or collected.get("tx_hash") or ""

    return {
        "crimeType": sub_name,
        "platform": platform,
        "username": username,
        "email": email,
        "phone": phone,
        "incidentDate": date_val,
        "incidentTime": time_val,
        "amountLost": str(amount_lost) if amount_lost else "",
        "transactionId": tx_id,
        "description": collected.get("fraud_description", ""),
        "missingFields": missing_fields
    }


@router.post("/chat")
async def chat_message(
    payload: ChatRequest,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> Dict[str, Any]:
    """
    Process a text chat message from the user.
    Primary path: Browser STT → transcript → this endpoint → Gemini → response text → Browser TTS.
    """
    session = db.query(AISession).filter(AISession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="AI session not found")

    if session.expires_at < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=400, detail="AI session has expired")

    # Link user to session if they just logged in
    if current_user and not session.user_id:
        session.user_id = current_user.id

    # Add user message to history
    history = list(session.conversation_history)
    history.append({
        "role": "user",
        "text": payload.message,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

    # Call unified Dialogue state machine turn processor
    result = await gemini_client.process_dialogue_turn(
        db=db,
        session=session,
        user_message=payload.message,
        confidence=payload.confidence or 1.0,
        user_logged_in=bool(current_user)
    )

    detected_cat = result.get("detected_category")
    detected_sub = result.get("detected_subcategory")
    response_text = result.get("response", "I understand. Please tell me more.")

    # Find DB IDs for category/subcategory
    cat_id = None
    sub_id = None
    if detected_cat:
        category = db.query(ComplaintCategory).filter(ComplaintCategory.name == detected_cat).first()
        if category:
            cat_id = category.id
            if detected_sub:
                subcategory = db.query(ComplaintSubcategory).filter(
                    ComplaintSubcategory.name == detected_sub,
                    ComplaintSubcategory.category_id == category.id
                ).first()
                if subcategory:
                    sub_id = subcategory.id

    if cat_id:
        session.detected_category_id = cat_id
    if sub_id:
        session.detected_subcategory_id = sub_id

    session.state = "COLLECTING_INFO"

    # Add assistant response to history
    history.append({
        "role": "assistant",
        "text": response_text,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    session.conversation_history = history
    session.expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

    # Try to generate TTS base64 (optional — frontend uses browser TTS as primary)
    audio_base64 = None
    try:
        audio_base64 = await sarvam_client.text_to_speech(response_text, session.language)
    except Exception as e:
        logger.info("TTS skipped for chat response: %s", str(e)[:100])

    db.commit()

    return {
        "session_id": session.id,
        "response": response_text,
        "detected_category": detected_cat,
        "detected_subcategory": detected_sub,
        "quality_score": result.get("quality_score", 10),
        "is_high_priority": result.get("is_high_priority", False),
        "is_complete": result.get("is_complete", False),
        "step": result.get("step", 1),
        "progress_breakdown": result.get("progress_breakdown"),
        "duplicate_warning": result.get("duplicate_warning"),
        "audio_base64": audio_base64,
        "audio_base_64": audio_base64,
        "language": session.language,
        "form_data": _get_session_form_data(session, db),
        "conversation_state": _get_conversation_state(session, db, []),
        "requires_auth": result.get("requires_auth", False)
    }


@router.post("/voice")
async def voice_message(
    session_id: str = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> Dict[str, Any]:
    """
    Process an audio recording (STT) and return the AI chat response (with TTS).
    This is the FALLBACK path — used only when browser SpeechRecognition is unavailable.
    Primary path uses browser STT → /chat endpoint → browser TTS.
    """
    session = db.query(AISession).filter(AISession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="AI session not found")

    if session.expires_at < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=400, detail="AI session has expired")

    # Link user to session if they just logged in
    if current_user and not session.user_id:
        session.user_id = current_user.id

    audio_bytes = await audio_file.read()

    # Transcribe via Sarvam (fallback provider)
    stt_result = await sarvam_client.speech_to_text(audio_bytes, filename=audio_file.filename)
    transcript = stt_result.get("transcript", "")
    detected_lang = stt_result.get("language_code", session.language)

    # If Sarvam failed or returned empty transcript
    if not transcript.strip():
        stt_error = stt_result.get("error", "")
        if stt_error:
            # Sarvam is unavailable — inform user to use text chat
            response_text = (
                "I'm sorry, our voice recognition service is temporarily unavailable. "
                "Please type your message in the chat box below, and I will assist you step by step."
            )
        else:
            response_text = "Sorry, I could not hear anything. Please try again."

        return {
            "session_id": session.id,
            "transcript": "",
            "detected_language": detected_lang,
            "response": response_text,
            "detected_category": None,
            "detected_subcategory": None,
            "quality_score": 10,
            "quality_details": [],
            "is_high_priority": False,
            "audio_base64": None,
            "audio_base_64": None,
            "language": session.language,
            "form_data": _get_session_form_data(session, db),
            "conversation_state": _get_conversation_state(session, db, []),
            "requires_auth": False
        }

    # If the user speaks in a different language, update the session language preference
    if detected_lang and detected_lang != session.language and detected_lang != "unknown":
        session.language = detected_lang

    # Add user transcript message to history
    history = list(session.conversation_history)
    history.append({
        "role": "user",
        "text": transcript,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })

    # Call unified Dialogue state machine turn processor
    result = await gemini_client.process_dialogue_turn(
        db=db,
        session=session,
        user_message=transcript,
        confidence=0.85, # STT fallback confidence default
        user_logged_in=bool(current_user)
    )

    detected_cat = result.get("detected_category")
    detected_sub = result.get("detected_subcategory")
    response_text = result.get("response", "I understand.")

    # Find DB IDs for category/subcategory
    cat_id = None
    sub_id = None
    if detected_cat:
        category = db.query(ComplaintCategory).filter(ComplaintCategory.name == detected_cat).first()
        if category:
            cat_id = category.id
            if detected_sub:
                subcategory = db.query(ComplaintSubcategory).filter(
                    ComplaintSubcategory.name == detected_sub,
                    ComplaintSubcategory.category_id == category.id
                ).first()
                if subcategory:
                    sub_id = subcategory.id

    if cat_id:
        session.detected_category_id = cat_id
    if sub_id:
        session.detected_subcategory_id = sub_id

    session.state = "COLLECTING_INFO"

    # Add assistant response to history
    history.append({
        "role": "assistant",
        "text": response_text,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    session.conversation_history = history
    session.expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

    # Generate TTS audio for response (optional)
    audio_base64 = None
    try:
        audio_base64 = await sarvam_client.text_to_speech(response_text, session.language)
    except Exception as e:
        logger.info("TTS skipped for voice response: %s", str(e)[:100])

    db.commit()

    return {
        "session_id": session.id,
        "transcript": transcript,
        "detected_language": detected_lang,
        "response": response_text,
        "detected_category": detected_cat,
        "detected_subcategory": detected_sub,
        "quality_score": result.get("quality_score", 10),
        "is_high_priority": result.get("is_high_priority", False),
        "is_complete": result.get("is_complete", False),
        "step": result.get("step", 1),
        "progress_breakdown": result.get("progress_breakdown"),
        "duplicate_warning": result.get("duplicate_warning"),
        "audio_base64": audio_base64,
        "audio_base_64": audio_base64,
        "language": session.language,
        "form_data": _get_session_form_data(session, db),
        "conversation_state": _get_conversation_state(session, db, []),
        "requires_auth": result.get("requires_auth", False)
    }


@router.post("/tts")
async def generate_tts(payload: TTSRequest) -> Dict[str, Any]:
    """
    Convert arbitrary text to speech base64 string.
    Falls back gracefully if Sarvam is unavailable.
    """
    try:
        audio_base64 = await sarvam_client.text_to_speech(payload.text, payload.language)
        if audio_base64:
            return {
                "audio_base_64": audio_base64,
                "audio_base64": audio_base64
            }
        else:
            # Sarvam returned None — service unavailable
            return {
                "audio_base_64": None,
                "audio_base64": None,
                "error": "TTS service unavailable — use browser speech synthesis"
            }
    except Exception as e:
        logger.warning("TTS endpoint: %s", str(e)[:100])
        return {
            "audio_base_64": None,
            "audio_base64": None,
            "error": "TTS service unavailable"
        }


@router.get("/session/{session_id}")
def get_session(
    session_id: str,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """Retrieve full details of an active assistant session."""
    session = db.query(AISession).filter(AISession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="AI session not found")

    return {
        "session_id": session.id,
        "state": session.state,
        "detected_category_id": session.detected_category_id,
        "detected_subcategory_id": session.detected_subcategory_id,
        "collected_data": session.collected_data,
        "conversation_history": session.conversation_history,
        "language": session.language,
        "is_expired": session.expires_at < datetime.datetime.now(datetime.timezone.utc)
    }


@router.get("/form-data/{session_id}")
def get_form_data(
    session_id: str,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """Format extracted information for frontend complaint form auto-fill."""
    session = db.query(AISession).filter(AISession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="AI session not found")

    return _get_session_form_data(session, db)


@router.post("/language")
def set_language(
    payload: LanguageRequest,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """Change the voice and conversation language for the session."""
    session = db.query(AISession).filter(AISession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="AI session not found")

    session.language = payload.language
    db.commit()
    return {"status": "success", "language": session.language}


@router.delete("/session/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(deps.get_db)
) -> Dict[str, Any]:
    """Remove session from DB."""
    session = db.query(AISession).filter(AISession.id == session_id).first()
    if session:
        db.delete(session)
        db.commit()
    return {"status": "success"}
